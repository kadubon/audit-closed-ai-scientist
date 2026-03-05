"""Optional-stopping simulation: peeking p-values vs always-valid e-values."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np

from audit_protocol.sequential_tests import run_grid_e_test
from baseline_ai_scientist.experiment_runner import one_sided_mean_positive_pvalue
from simulations.stat_utils import wilson_interval


def _naive_peeking_decision(samples: np.ndarray, alpha: float) -> Dict[str, float | bool | int]:
    crossed = False
    stopping_time = len(samples)
    for look in range(5, len(samples) + 1):
        p_value, _ = one_sided_mean_positive_pvalue(samples[:look])
        if p_value < alpha:
            crossed = True
            stopping_time = look
            break
    return {"crossed": crossed, "stopping_time": int(stopping_time)}


def _fixed_horizon_pvalue_decision(samples: np.ndarray, alpha: float) -> Dict[str, float | bool | int]:
    p_value, _ = one_sided_mean_positive_pvalue(samples)
    crossed = bool(p_value < alpha)
    return {"crossed": crossed, "stopping_time": len(samples)}


def _evalue_decision(samples: np.ndarray, alpha: float) -> Dict[str, float | bool | int]:
    increments = np.clip(samples / 3.0, -1.0, 1.0)
    result = run_grid_e_test(
        increments=np.asarray(increments, dtype=float),
        alpha_epoch=alpha,
        n_candidates=1,
        stop_on_threshold=True,
    )
    return {
        "crossed": bool(result.crossed_threshold),
        "stopping_time": int(result.stopping_time),
        "final_e_value": float(result.final_e_value),
    }


def _trial(max_looks: int, mean_shift: float, alpha: float, rng: np.random.Generator) -> Dict[str, object]:
    samples = rng.normal(loc=mean_shift, scale=1.0, size=max_looks)
    p_peek = _naive_peeking_decision(samples=samples, alpha=alpha)
    p_fixed = _fixed_horizon_pvalue_decision(samples=samples, alpha=alpha)
    e_decision = _evalue_decision(samples=samples, alpha=alpha)
    return {"p_peek": p_peek, "p_fixed": p_fixed, "e": e_decision}


def _summarize_trials(trials: List[Dict[str, object]], key: str) -> Dict[str, float]:
    crossed = np.asarray([bool(trial[key]["crossed"]) for trial in trials], dtype=bool)
    stopping_times = np.asarray([int(trial[key]["stopping_time"]) for trial in trials], dtype=float)
    ci = wilson_interval(int(np.sum(crossed)), len(trials))
    return {
        "crossing_rate": ci["rate"],
        "crossing_rate_ci_low": ci["ci_low"],
        "crossing_rate_ci_high": ci["ci_high"],
        "median_stopping_time": float(np.median(stopping_times[crossed])) if np.any(crossed) else float("nan"),
    }


def run_simulation(
    alpha: float = 0.05,
    max_looks_grid: Iterable[int] = (20, 50, 100, 200, 400),
    n_runs_null: int = 1200,
    n_runs_alt: int = 700,
    alt_mean_shift: float = 0.2,
    seed: int = 2028,
    output_path: str | None = None,
) -> Dict[str, object]:
    rng = np.random.default_rng(seed)
    reliability: List[Dict[str, float]] = []
    for max_looks in max_looks_grid:
        null_trials = [
            _trial(max_looks=max_looks, mean_shift=0.0, alpha=alpha, rng=rng)
            for _ in range(n_runs_null)
        ]
        p_peek_stats = _summarize_trials(null_trials, key="p_peek")
        p_fixed_stats = _summarize_trials(null_trials, key="p_fixed")
        e_stats = _summarize_trials(null_trials, key="e")
        reliability.append(
            {
                "max_looks": int(max_looks),
                "p_value_false_positive_rate_peeking": p_peek_stats["crossing_rate"],
                "p_value_false_positive_rate_peeking_ci_low": p_peek_stats["crossing_rate_ci_low"],
                "p_value_false_positive_rate_peeking_ci_high": p_peek_stats["crossing_rate_ci_high"],
                "p_value_false_positive_rate_fixed_horizon": p_fixed_stats["crossing_rate"],
                "p_value_false_positive_rate_fixed_horizon_ci_low": p_fixed_stats["crossing_rate_ci_low"],
                "p_value_false_positive_rate_fixed_horizon_ci_high": p_fixed_stats["crossing_rate_ci_high"],
                "e_value_false_positive_rate_sequential": e_stats["crossing_rate"],
                "e_value_false_positive_rate_sequential_ci_low": e_stats["crossing_rate_ci_low"],
                "e_value_false_positive_rate_sequential_ci_high": e_stats["crossing_rate_ci_high"],
            }
        )

    alt_max_looks = int(max(max_looks_grid))
    alt_trials = [
        _trial(max_looks=alt_max_looks, mean_shift=alt_mean_shift, alpha=alpha, rng=rng)
        for _ in range(n_runs_alt)
    ]
    p_peek_alt = _summarize_trials(alt_trials, key="p_peek")
    p_fixed_alt = _summarize_trials(alt_trials, key="p_fixed")
    e_alt = _summarize_trials(alt_trials, key="e")

    result: Dict[str, object] = {
        "simulation": "optional_stopping",
        "alpha": alpha,
        "n_runs_null": n_runs_null,
        "n_runs_alt": n_runs_alt,
        "confidence_level": 0.95,
        "alt_mean_shift": alt_mean_shift,
        "false_positive_by_max_looks": reliability,
        "alternative_detection_rate_p_value_peeking": p_peek_alt["crossing_rate"],
        "alternative_detection_rate_p_value_fixed_horizon": p_fixed_alt["crossing_rate"],
        "alternative_detection_rate_e_value_sequential": e_alt["crossing_rate"],
        "alternative_median_stop_p_value_peeking": p_peek_alt["median_stopping_time"],
        "alternative_median_stop_e_value_sequential": e_alt["median_stopping_time"],
    }
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    data = run_simulation()
    print(json.dumps(data, indent=2))
