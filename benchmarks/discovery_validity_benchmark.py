"""End-to-end benchmark for discovery validity in autonomous AI scientist systems."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import numpy as np

from audit_protocol.audit_closed_update import AuditClosedConfig, AuditClosedScientist
from baseline_ai_scientist.experiment_runner import evaluate_candidate, generate_synthetic_data, split_train_test
from baseline_ai_scientist.hypothesis_generator import find_candidate_by_name, generate_hypotheses
from simulations.adversarial_agents import run_simulation as run_adversarial_simulation
from simulations.optional_stopping import run_simulation as run_optional_stopping_simulation
from simulations.stat_utils import wilson_interval


def _replication_check(candidate_name: str, signal: bool, seed: int) -> bool:
    candidates = generate_hypotheses(n_candidates=120, seed=seed, include_defaults=True)
    candidate = find_candidate_by_name(candidates, candidate_name)
    if candidate is None:
        return False

    data = generate_synthetic_data(
        n_samples=180,
        noise_std=0.35,
        seed=seed + 1,
        signal=signal,
    )
    x_train, y_train, x_test, y_test = split_train_test(data.x, data.y, train_fraction=0.5)
    metrics = evaluate_candidate(candidate, x_train, y_train, x_test, y_test)
    return bool(metrics["p_value"] < 0.05 and metrics["mean_improvement"] > 0.0)


def _run_budget_matched_trials(
    n_runs: int,
    signal: bool,
    seed: int,
    alpha: float = 0.05,
    n_candidates: int = 50,
    n_samples: int = 180,
) -> Dict[str, object]:
    rng = np.random.default_rng(seed)
    baseline_accept = 0
    baseline_replicate = 0
    audit_accept = 0
    audit_replicate = 0

    config = AuditClosedConfig(total_alpha=2.0 * alpha, alpha_decay=0.5)
    for _ in range(n_runs):
        run_seed = int(rng.integers(0, 2**31 - 1))
        data = generate_synthetic_data(
            n_samples=n_samples,
            noise_std=0.35,
            seed=run_seed,
            signal=signal,
        )
        candidates = generate_hypotheses(
            n_candidates=n_candidates,
            seed=run_seed + 1,
            include_defaults=True,
        )

        # Baseline batch selection (candidate-shopping without multiplicity control).
        x_train, y_train, x_test, y_test = split_train_test(data.x, data.y, train_fraction=0.5)
        best_name = None
        best_p = 1.0
        for candidate in candidates:
            pval = evaluate_candidate(candidate, x_train, y_train, x_test, y_test)["p_value"]
            if pval < best_p:
                best_p = float(pval)
                best_name = candidate.name
        baseline_decision = best_p < alpha
        if baseline_decision and best_name is not None:
            baseline_accept += 1
            if _replication_check(best_name, signal=signal, seed=run_seed + 2):
                baseline_replicate += 1

        # Audit-closed selection (same candidate set and data budget).
        scientist = AuditClosedScientist(config=config, seed=run_seed)
        decision = scientist.evaluate_epoch(epoch=0, candidates=candidates, x=data.x, y=data.y)
        replay = scientist.replay_epoch(epoch=0)
        if not replay["replay_matches"] or not replay["log_integrity_ok"]:
            raise RuntimeError("audit-closed replay/integrity check failed")
        if decision["accepted"] and decision["winner"] is not None:
            audit_accept += 1
            if _replication_check(decision["winner"], signal=signal, seed=run_seed + 3):
                audit_replicate += 1

    baseline_accept_ci = wilson_interval(baseline_accept, n_runs)
    audit_accept_ci = wilson_interval(audit_accept, n_runs)
    baseline_rep_ci = wilson_interval(baseline_replicate, baseline_accept) if baseline_accept > 0 else {
        "rate": 0.0,
        "ci_low": 0.0,
        "ci_high": 0.0,
    }
    audit_rep_ci = wilson_interval(audit_replicate, audit_accept) if audit_accept > 0 else {
        "rate": 0.0,
        "ci_low": 0.0,
        "ci_high": 0.0,
    }

    return {
        "n_runs": n_runs,
        "alpha": alpha,
        "n_candidates": n_candidates,
        "n_samples": n_samples,
        "baseline_accept_rate": baseline_accept_ci["rate"],
        "baseline_accept_rate_ci_low": baseline_accept_ci["ci_low"],
        "baseline_accept_rate_ci_high": baseline_accept_ci["ci_high"],
        "audit_accept_rate": audit_accept_ci["rate"],
        "audit_accept_rate_ci_low": audit_accept_ci["ci_low"],
        "audit_accept_rate_ci_high": audit_accept_ci["ci_high"],
        "baseline_replication_success_rate": baseline_rep_ci["rate"],
        "baseline_replication_success_rate_ci_low": baseline_rep_ci["ci_low"],
        "baseline_replication_success_rate_ci_high": baseline_rep_ci["ci_high"],
        "audit_replication_success_rate": audit_rep_ci["rate"],
        "audit_replication_success_rate_ci_low": audit_rep_ci["ci_low"],
        "audit_replication_success_rate_ci_high": audit_rep_ci["ci_high"],
        "baseline_accepted_trials": int(baseline_accept),
        "audit_accepted_trials": int(audit_accept),
    }


def run_benchmark(
    n_runs: int = 320,
    seed: int = 2030,
    output_path: str | None = None,
) -> Dict[str, object]:
    null = _run_budget_matched_trials(n_runs=n_runs, signal=False, seed=seed)
    alt = _run_budget_matched_trials(n_runs=n_runs, signal=True, seed=seed + 1)

    optional = run_optional_stopping_simulation(
        alpha=0.05,
        max_looks_grid=(20, 50, 100, 200, 400),
        n_runs_null=1000,
        n_runs_alt=500,
        seed=seed + 2,
    )
    p_peek_rates = np.asarray(
        [row["p_value_false_positive_rate_peeking"] for row in optional["false_positive_by_max_looks"]],
        dtype=float,
    )
    e_rates = np.asarray(
        [row["e_value_false_positive_rate_sequential"] for row in optional["false_positive_by_max_looks"]],
        dtype=float,
    )
    evidence_stability = {
        "nominal_alpha": 0.05,
        "p_value_peeking_alpha_deviation": float(np.mean(np.abs(p_peek_rates - 0.05))),
        "e_value_sequential_alpha_deviation": float(np.mean(np.abs(e_rates - 0.05))),
    }

    adversarial = run_adversarial_simulation(
        malicious_counts=(100,),
        n_runs=400,
        seed=seed + 3,
    )
    adversarial_point = adversarial["robustness_curve"][0]
    robustness = {
        "baseline_false_accept_rate": float(adversarial_point["baseline_false_accept_rate"]),
        "baseline_false_accept_rate_ci_low": float(adversarial_point["baseline_false_accept_rate_ci_low"]),
        "baseline_false_accept_rate_ci_high": float(adversarial_point["baseline_false_accept_rate_ci_high"]),
        "audit_false_accept_rate": float(adversarial_point["audit_false_accept_rate"]),
        "audit_false_accept_rate_ci_low": float(adversarial_point["audit_false_accept_rate_ci_low"]),
        "audit_false_accept_rate_ci_high": float(adversarial_point["audit_false_accept_rate_ci_high"]),
        "tamper_detection_rate": float(adversarial_point["tamper_detection_rate"]),
        "baseline_robustness": float(1.0 - adversarial_point["baseline_false_accept_rate"]),
        "audit_robustness": float(1.0 - adversarial_point["audit_false_accept_rate"]),
    }

    result: Dict[str, object] = {
        "benchmark": "discovery_validity_benchmark",
        "n_runs": n_runs,
        "confidence_level": 0.95,
        "budget_matched_setup": {
            "n_candidates_per_trial": int(null["n_candidates"]),
            "n_samples_per_trial": int(null["n_samples"]),
            "decision_alpha": float(null["alpha"]),
        },
        "false_discovery_rate": {
            "baseline": float(null["baseline_accept_rate"]),
            "baseline_ci_low": float(null["baseline_accept_rate_ci_low"]),
            "baseline_ci_high": float(null["baseline_accept_rate_ci_high"]),
            "audit_closed": float(null["audit_accept_rate"]),
            "audit_closed_ci_low": float(null["audit_accept_rate_ci_low"]),
            "audit_closed_ci_high": float(null["audit_accept_rate_ci_high"]),
        },
        "replicability": {
            "baseline_acceptance_rate": float(alt["baseline_accept_rate"]),
            "baseline_acceptance_rate_ci_low": float(alt["baseline_accept_rate_ci_low"]),
            "baseline_acceptance_rate_ci_high": float(alt["baseline_accept_rate_ci_high"]),
            "audit_acceptance_rate": float(alt["audit_accept_rate"]),
            "audit_acceptance_rate_ci_low": float(alt["audit_accept_rate_ci_low"]),
            "audit_acceptance_rate_ci_high": float(alt["audit_accept_rate_ci_high"]),
            "baseline_replication_success_rate": float(alt["baseline_replication_success_rate"]),
            "baseline_replication_success_rate_ci_low": float(alt["baseline_replication_success_rate_ci_low"]),
            "baseline_replication_success_rate_ci_high": float(alt["baseline_replication_success_rate_ci_high"]),
            "audit_replication_success_rate": float(alt["audit_replication_success_rate"]),
            "audit_replication_success_rate_ci_low": float(alt["audit_replication_success_rate_ci_low"]),
            "audit_replication_success_rate_ci_high": float(alt["audit_replication_success_rate_ci_high"]),
            "baseline_accepted_trials": int(alt["baseline_accepted_trials"]),
            "audit_accepted_trials": int(alt["audit_accepted_trials"]),
        },
        "evidence_stability_under_sequential_testing": evidence_stability,
        "robustness_to_adversarial_experiments": robustness,
    }

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    benchmark = run_benchmark()
    print(json.dumps(benchmark, indent=2))
