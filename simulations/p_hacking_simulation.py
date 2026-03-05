"""Simulation of many-hypothesis inflation and p-hacking in naive pipelines."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np

from baseline_ai_scientist.experiment_runner import one_sided_mean_positive_pvalue
from simulations.stat_utils import wilson_interval


def _single_min_pvalue(
    n_hypotheses: int,
    rng: np.random.Generator,
    n_samples: int = 60,
) -> float:
    # Emulates searching many null hypotheses and publishing the smallest p-value.
    min_p = 1.0
    for _ in range(n_hypotheses):
        null_samples = rng.normal(loc=0.0, scale=1.0, size=n_samples)
        p_value, _ = one_sided_mean_positive_pvalue(null_samples)
        min_p = min(min_p, float(p_value))
    return float(min_p)


def run_simulation(
    hypothesis_counts: Iterable[int] = (5, 20, 50, 100, 250, 500, 1000),
    n_runs: int = 300,
    alpha: float = 0.05,
    seed: int = 2026,
    output_path: str | None = None,
) -> Dict[str, object]:
    rng = np.random.default_rng(seed)
    summary: List[Dict[str, float]] = []

    for n_hypotheses in hypothesis_counts:
        min_pvalues = [_single_min_pvalue(int(n_hypotheses), rng=rng) for _ in range(n_runs)]
        min_pvalues_arr = np.asarray(min_pvalues, dtype=float)
        naive_successes = int(np.sum(min_pvalues_arr < alpha))
        bonf_successes = int(np.sum(min_pvalues_arr < (alpha / n_hypotheses)))
        naive_ci = wilson_interval(naive_successes, n_runs)
        bonf_ci = wilson_interval(bonf_successes, n_runs)
        independent_theory = 1.0 - (1.0 - alpha) ** int(n_hypotheses)
        summary.append(
            {
                "n_hypotheses": int(n_hypotheses),
                "false_discovery_rate_naive": naive_ci["rate"],
                "false_discovery_rate_naive_ci_low": naive_ci["ci_low"],
                "false_discovery_rate_naive_ci_high": naive_ci["ci_high"],
                "false_discovery_rate_bonferroni": bonf_ci["rate"],
                "false_discovery_rate_bonferroni_ci_low": bonf_ci["ci_low"],
                "false_discovery_rate_bonferroni_ci_high": bonf_ci["ci_high"],
                "independent_null_theory_naive": float(independent_theory),
                "median_min_p_value": float(np.median(min_pvalues)),
                "mean_min_p_value": float(np.mean(min_pvalues)),
            }
        )

    result: Dict[str, object] = {
        "simulation": "p_hacking_simulation",
        "alpha": alpha,
        "n_runs": n_runs,
        "confidence_level": 0.95,
        "false_discovery_rate_by_hypothesis_count": summary,
    }

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    data = run_simulation()
    print(json.dumps(data, indent=2))
