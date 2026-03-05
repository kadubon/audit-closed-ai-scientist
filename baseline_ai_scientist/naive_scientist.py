"""Naive AI scientist that is vulnerable to candidate shopping and p-hacking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np

from baseline_ai_scientist.experiment_runner import (
    evaluate_candidate,
    generate_synthetic_data,
    split_train_test,
)
from baseline_ai_scientist.hypothesis_generator import CandidateModel, generate_hypotheses


@dataclass
class NaiveScientistConfig:
    alpha: float = 0.05
    max_rounds: int = 8
    hypotheses_per_round: int = 40
    samples_per_round: int = 120
    noise_std: float = 0.35
    stop_on_significance: bool = True


class NaiveAIScientist:
    """A baseline pipeline that repeatedly searches and peeks until significance."""

    def __init__(self, config: NaiveScientistConfig | None = None, seed: int = 0):
        self.config = config or NaiveScientistConfig()
        self.rng = np.random.default_rng(seed)

    def run_discovery(
        self,
        signal: bool,
        signal_strength: float = 1.0,
        include_history: bool = False,
    ) -> Dict[str, Any]:
        history: List[Dict[str, float | int | str]] = []
        best_candidate: CandidateModel | None = None
        best_metrics: Dict[str, float] | None = None
        stopping_round = self.config.max_rounds - 1

        for round_idx in range(self.config.max_rounds):
            data_seed = int(self.rng.integers(0, 2**31 - 1))
            candidate_seed = int(self.rng.integers(0, 2**31 - 1))
            data = generate_synthetic_data(
                n_samples=self.config.samples_per_round,
                noise_std=self.config.noise_std,
                seed=data_seed,
                signal=signal,
                signal_strength=signal_strength,
            )
            x_train, y_train, x_test, y_test = split_train_test(data.x, data.y, train_fraction=0.5)
            hypotheses = generate_hypotheses(
                n_candidates=self.config.hypotheses_per_round,
                seed=candidate_seed,
                include_defaults=True,
            )

            for candidate in hypotheses:
                metrics = evaluate_candidate(candidate, x_train, y_train, x_test, y_test)
                history.append(
                    {
                        "round": round_idx,
                        "candidate": candidate.name,
                        "p_value": float(metrics["p_value"]),
                        "mean_improvement": float(metrics["mean_improvement"]),
                    }
                )
                if best_metrics is None or metrics["p_value"] < best_metrics["p_value"]:
                    best_metrics = metrics
                    best_candidate = candidate

            if (
                self.config.stop_on_significance
                and best_metrics is not None
                and best_metrics["p_value"] < self.config.alpha
            ):
                stopping_round = round_idx
                break

        assert best_metrics is not None
        accepted = best_metrics["p_value"] < self.config.alpha
        result: Dict[str, Any] = {
            "accepted": accepted,
            "alpha": self.config.alpha,
            "best_candidate_name": best_candidate.name if best_candidate else None,
            "best_candidate": best_candidate,
            "best_p_value": float(best_metrics["p_value"]),
            "best_mean_improvement": float(best_metrics["mean_improvement"]),
            "rounds_used": int(stopping_round + 1),
            "attempted_hypotheses": int(len(history)),
        }
        if include_history:
            result["history"] = history
        return result
