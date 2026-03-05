"""Public API for integrating this benchmark with external AI scientist systems."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Literal, Mapping, Protocol, Sequence

import numpy as np

from baseline_ai_scientist.experiment_runner import evaluate_candidate, generate_synthetic_data, split_train_test
from baseline_ai_scientist.hypothesis_generator import CandidateModel, generate_hypotheses
from benchmarks.discovery_validity_benchmark import run_benchmark
from simulations.adversarial_agents import run_simulation as run_adversarial_simulation
from simulations.candidate_shopping import run_simulation as run_candidate_shopping_simulation
from simulations.certificate_schema_validation import run_simulation as run_certificate_schema_validation_simulation
from simulations.drift_localization_simulation import run_simulation as run_drift_localization_simulation
from simulations.optional_stopping import run_simulation as run_optional_stopping_simulation
from simulations.p_hacking_simulation import run_simulation as run_p_hacking_simulation
from simulations.power_curve import run_simulation as run_power_curve_simulation
from simulations.sentinel_hierarchy import run_simulation as run_sentinel_hierarchy_simulation
from simulations.stat_utils import wilson_interval


RunProfile = Literal["quick", "standard"]


@dataclass(frozen=True)
class SimulationBundleConfig:
    profile: RunProfile = "standard"
    alpha: float = 0.05

    @property
    def sizes(self) -> Dict[str, int]:
        if self.profile == "quick":
            return {
                "p_hacking_runs": 120,
                "candidate_shopping_runs": 140,
                "optional_null_runs": 500,
                "optional_alt_runs": 250,
                "power_curve_runs": 300,
                "adversarial_runs": 220,
                "sentinel_hierarchy_runs": 600,
                "drift_localization_runs": 500,
                "certificate_invalid_runs": 300,
                "benchmark_runs": 140,
            }
        return {
            "p_hacking_runs": 300,
            "candidate_shopping_runs": 350,
            "optional_null_runs": 1200,
            "optional_alt_runs": 700,
            "power_curve_runs": 800,
            "adversarial_runs": 500,
            "sentinel_hierarchy_runs": 1800,
            "drift_localization_runs": 1400,
            "certificate_invalid_runs": 800,
            "benchmark_runs": 320,
        }


class ExternalScientist(Protocol):
    """Protocol for external AI scientist adapters."""

    def evaluate_trial(
        self,
        *,
        candidates: Sequence[CandidateModel],
        x: np.ndarray,
        y: np.ndarray,
        alpha: float,
        seed: int,
        signal: bool,
    ) -> Mapping[str, Any]:
        """Return at minimum {'accepted': bool, 'winner': str|None}."""


@dataclass(frozen=True)
class ExternalEvaluationConfig:
    n_runs: int = 320
    alpha: float = 0.05
    n_candidates: int = 50
    n_samples: int = 180
    noise_std: float = 0.35
    signal_strength: float = 1.0
    seed: int = 2040


def _replication_check(
    *,
    candidate: CandidateModel,
    signal: bool,
    alpha: float,
    signal_strength: float,
    noise_std: float,
    seed: int,
) -> bool:
    data = generate_synthetic_data(
        n_samples=180,
        noise_std=noise_std,
        seed=seed,
        signal=signal,
        signal_strength=signal_strength,
    )
    x_train, y_train, x_test, y_test = split_train_test(data.x, data.y, train_fraction=0.5)
    metrics = evaluate_candidate(candidate, x_train, y_train, x_test, y_test)
    return bool(metrics["p_value"] < alpha and metrics["mean_improvement"] > 0.0)


def _call_external_scientist(
    scientist: ExternalScientist | Callable[..., Mapping[str, Any]],
    *,
    candidates: Sequence[CandidateModel],
    x: np.ndarray,
    y: np.ndarray,
    alpha: float,
    seed: int,
    signal: bool,
) -> Mapping[str, Any]:
    if hasattr(scientist, "evaluate_trial"):
        return scientist.evaluate_trial(
            candidates=candidates,
            x=x,
            y=y,
            alpha=alpha,
            seed=seed,
            signal=signal,
        )
    if callable(scientist):
        return scientist(
            candidates=candidates,
            x=x,
            y=y,
            alpha=alpha,
            seed=seed,
            signal=signal,
        )
    raise TypeError("external scientist must be callable or implement evaluate_trial(...)")


def _parse_external_decision(decision: Mapping[str, Any]) -> tuple[bool, str | None]:
    if "accepted" not in decision:
        raise ValueError("external decision is missing required key: accepted")
    accepted = bool(decision["accepted"])
    winner = decision.get("winner", decision.get("best_candidate_name"))
    if winner is not None and not isinstance(winner, str):
        raise ValueError("external decision winner must be a string or None")
    return accepted, winner


class DiscoveryValidityHarness:
    """Harness exposing benchmark.evaluate(my_ai_scientist)."""

    def __init__(self, config: ExternalEvaluationConfig = ExternalEvaluationConfig()) -> None:
        self.config = config

    def _run_condition(
        self,
        scientist: ExternalScientist | Callable[..., Mapping[str, Any]],
        *,
        signal: bool,
        seed: int,
    ) -> Dict[str, float | int]:
        rng = np.random.default_rng(seed)
        accepted = 0
        replicated = 0
        interface_errors = 0
        invalid_winner = 0

        for _ in range(self.config.n_runs):
            run_seed = int(rng.integers(0, 2**31 - 1))
            data = generate_synthetic_data(
                n_samples=self.config.n_samples,
                noise_std=self.config.noise_std,
                seed=run_seed,
                signal=signal,
                signal_strength=self.config.signal_strength,
            )
            candidates = generate_hypotheses(
                n_candidates=self.config.n_candidates,
                seed=run_seed + 1,
                include_defaults=True,
            )
            by_name = {candidate.name: candidate for candidate in candidates}

            try:
                decision = _call_external_scientist(
                    scientist,
                    candidates=candidates,
                    x=data.x,
                    y=data.y,
                    alpha=self.config.alpha,
                    seed=run_seed,
                    signal=signal,
                )
                is_accepted, winner = _parse_external_decision(decision)
            except Exception:
                interface_errors += 1
                continue

            if not is_accepted:
                continue
            accepted += 1
            if winner is None or winner not in by_name:
                invalid_winner += 1
                continue

            if _replication_check(
                candidate=by_name[winner],
                signal=signal,
                alpha=self.config.alpha,
                signal_strength=self.config.signal_strength,
                noise_std=self.config.noise_std,
                seed=run_seed + 2,
            ):
                replicated += 1

        accept_ci = wilson_interval(accepted, self.config.n_runs)
        repl_ci = (
            wilson_interval(replicated, accepted)
            if accepted > 0
            else {"rate": 0.0, "ci_low": 0.0, "ci_high": 0.0}
        )
        invalid_ci = wilson_interval(invalid_winner, accepted) if accepted > 0 else {
            "rate": 0.0,
            "ci_low": 0.0,
            "ci_high": 0.0,
        }
        error_ci = wilson_interval(interface_errors, self.config.n_runs)

        return {
            "accept_rate": float(accept_ci["rate"]),
            "accept_rate_ci_low": float(accept_ci["ci_low"]),
            "accept_rate_ci_high": float(accept_ci["ci_high"]),
            "replication_rate": float(repl_ci["rate"]),
            "replication_rate_ci_low": float(repl_ci["ci_low"]),
            "replication_rate_ci_high": float(repl_ci["ci_high"]),
            "invalid_winner_rate_among_accepts": float(invalid_ci["rate"]),
            "interface_error_rate": float(error_ci["rate"]),
            "accepted_trials": int(accepted),
            "replicated_trials": int(replicated),
            "interface_error_trials": int(interface_errors),
            "invalid_winner_trials": int(invalid_winner),
        }

    def evaluate(
        self,
        scientist: ExternalScientist | Callable[..., Mapping[str, Any]],
    ) -> Dict[str, object]:
        """Evaluate an external AI scientist under the benchmark data protocol."""
        null_result = self._run_condition(scientist, signal=False, seed=self.config.seed)
        alt_result = self._run_condition(scientist, signal=True, seed=self.config.seed + 1)
        return {
            "benchmark": "external_scientist_evaluation",
            "config": {
                "n_runs": self.config.n_runs,
                "alpha": self.config.alpha,
                "n_candidates": self.config.n_candidates,
                "n_samples": self.config.n_samples,
                "noise_std": self.config.noise_std,
                "signal_strength": self.config.signal_strength,
                "seed": self.config.seed,
            },
            "null_world": {
                "false_discovery_rate": null_result["accept_rate"],
                "false_discovery_rate_ci_low": null_result["accept_rate_ci_low"],
                "false_discovery_rate_ci_high": null_result["accept_rate_ci_high"],
            },
            "signal_world": {
                "acceptance_rate": alt_result["accept_rate"],
                "acceptance_rate_ci_low": alt_result["accept_rate_ci_low"],
                "acceptance_rate_ci_high": alt_result["accept_rate_ci_high"],
                "replication_probability": alt_result["replication_rate"],
                "replication_probability_ci_low": alt_result["replication_rate_ci_low"],
                "replication_probability_ci_high": alt_result["replication_rate_ci_high"],
            },
            "interface_diagnostics": {
                "null_world_error_rate": null_result["interface_error_rate"],
                "signal_world_error_rate": alt_result["interface_error_rate"],
                "null_invalid_winner_rate": null_result["invalid_winner_rate_among_accepts"],
                "signal_invalid_winner_rate": alt_result["invalid_winner_rate_among_accepts"],
            },
        }


class Benchmark:
    """Simple facade exposing benchmark.evaluate(my_ai_scientist)."""

    def __init__(self, config: ExternalEvaluationConfig = ExternalEvaluationConfig()) -> None:
        self.harness = DiscoveryValidityHarness(config=config)

    def evaluate(self, scientist: ExternalScientist | Callable[..., Mapping[str, Any]]) -> Dict[str, object]:
        return self.harness.evaluate(scientist)


benchmark = Benchmark()


def run_simulation_bundle(config: SimulationBundleConfig = SimulationBundleConfig()) -> Dict[str, object]:
    """Run all benchmark simulations as a reusable API call."""
    sizes = config.sizes
    return {
        "p_hacking_simulation": run_p_hacking_simulation(
            n_runs=sizes["p_hacking_runs"],
            alpha=config.alpha,
            seed=2026,
        ),
        "candidate_shopping": run_candidate_shopping_simulation(
            n_runs=sizes["candidate_shopping_runs"],
            alpha=config.alpha,
            seed=2027,
        ),
        "optional_stopping": run_optional_stopping_simulation(
            n_runs_null=sizes["optional_null_runs"],
            n_runs_alt=sizes["optional_alt_runs"],
            alpha=config.alpha,
            seed=2028,
        ),
        "power_curve": run_power_curve_simulation(
            n_runs=sizes["power_curve_runs"],
            alpha=config.alpha,
            seed=2031,
        ),
        "adversarial_agents": run_adversarial_simulation(
            n_runs=sizes["adversarial_runs"],
            alpha=config.alpha,
            seed=2029,
        ),
        "sentinel_hierarchy": run_sentinel_hierarchy_simulation(
            n_runs=sizes["sentinel_hierarchy_runs"],
            seed=2032,
        ),
        "drift_localization": run_drift_localization_simulation(
            n_runs=sizes["drift_localization_runs"],
            seed=2033,
        ),
        "certificate_schema_validation": run_certificate_schema_validation_simulation(
            n_valid=max(100, sizes["certificate_invalid_runs"] // 2),
            n_invalid=sizes["certificate_invalid_runs"],
            seed=2034,
        ),
        "benchmark": run_benchmark(
            n_runs=sizes["benchmark_runs"],
            seed=2030,
        ),
    }
