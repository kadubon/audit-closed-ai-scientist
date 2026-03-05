"""Detection power curves for peeking p-values, fixed p-values, and e-values."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np

from audit_protocol.sequential_tests import run_grid_e_test
from baseline_ai_scientist.experiment_runner import one_sided_mean_positive_pvalue
from simulations.stat_utils import wilson_interval


def _naive_peeking_decision(samples: np.ndarray, alpha: float) -> bool:
    for look in range(5, len(samples) + 1):
        p_value, _ = one_sided_mean_positive_pvalue(samples[:look])
        if p_value < alpha:
            return True
    return False


def _fixed_horizon_decision(samples: np.ndarray, alpha: float) -> bool:
    p_value, _ = one_sided_mean_positive_pvalue(samples)
    return bool(p_value < alpha)


def _evalue_decision(samples: np.ndarray, alpha: float) -> bool:
    increments = np.clip(samples / 3.0, -1.0, 1.0)
    result = run_grid_e_test(
        increments=np.asarray(increments, dtype=float),
        alpha_epoch=alpha,
        n_candidates=1,
        stop_on_threshold=True,
    )
    return bool(result.crossed_threshold)


def run_simulation(
    effect_sizes: Iterable[float] = (0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4),
    n_runs: int = 800,
    max_looks: int = 250,
    alpha: float = 0.05,
    seed: int = 2031,
    output_path: str | None = None,
) -> Dict[str, object]:
    rng = np.random.default_rng(seed)
    rows: List[Dict[str, float]] = []

    for effect in effect_sizes:
        p_peek_count = 0
        p_fixed_count = 0
        e_count = 0
        for _ in range(n_runs):
            samples = rng.normal(loc=float(effect), scale=1.0, size=max_looks)
            if _naive_peeking_decision(samples, alpha=alpha):
                p_peek_count += 1
            if _fixed_horizon_decision(samples, alpha=alpha):
                p_fixed_count += 1
            if _evalue_decision(samples, alpha=alpha):
                e_count += 1

        p_peek_ci = wilson_interval(p_peek_count, n_runs)
        p_fixed_ci = wilson_interval(p_fixed_count, n_runs)
        e_ci = wilson_interval(e_count, n_runs)
        rows.append(
            {
                "effect_size": float(effect),
                "peeking_p_detection_rate": p_peek_ci["rate"],
                "peeking_p_detection_rate_ci_low": p_peek_ci["ci_low"],
                "peeking_p_detection_rate_ci_high": p_peek_ci["ci_high"],
                "fixed_p_detection_rate": p_fixed_ci["rate"],
                "fixed_p_detection_rate_ci_low": p_fixed_ci["ci_low"],
                "fixed_p_detection_rate_ci_high": p_fixed_ci["ci_high"],
                "e_value_detection_rate": e_ci["rate"],
                "e_value_detection_rate_ci_low": e_ci["ci_low"],
                "e_value_detection_rate_ci_high": e_ci["ci_high"],
            }
        )

    result: Dict[str, object] = {
        "simulation": "power_curve",
        "alpha": alpha,
        "n_runs": n_runs,
        "max_looks": max_looks,
        "confidence_level": 0.95,
        "rows": rows,
    }
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    payload = run_simulation()
    print(json.dumps(payload, indent=2))
