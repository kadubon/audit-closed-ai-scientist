"""Candidate-shopping simulation comparing naive and audit-closed selection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np

from audit_protocol.sequential_tests import run_grid_e_test
from baseline_ai_scientist.experiment_runner import (
    evaluate_candidate,
    generate_synthetic_data,
    prepare_candidate_increment_stream,
    split_train_test,
)
from baseline_ai_scientist.hypothesis_generator import default_hypotheses, find_candidate_by_name
from simulations.stat_utils import wilson_interval


def _draw_design(rng: np.random.Generator) -> Dict[str, float]:
    width = float(rng.uniform(0.8, 2.0) * np.pi)
    center = float(rng.uniform(-1.0, 1.0))
    x_range = (center - width, center + width)
    n_samples = int(rng.integers(70, 150))
    noise_std = float(rng.uniform(0.25, 0.45))
    return {"x_min": x_range[0], "x_max": x_range[1], "n_samples": n_samples, "noise_std": noise_std}


def _design_statistics(
    candidate_name: str,
    signal: bool,
    signal_strength: float,
    n_designs: int,
    alpha: float,
    rng: np.random.Generator,
) -> Dict[str, float]:
    candidate = find_candidate_by_name(default_hypotheses(), candidate_name)
    if candidate is None:
        raise ValueError(f"candidate {candidate_name} not found")

    min_p = 1.0
    max_e = 0.0
    for _ in range(n_designs):
        design = _draw_design(rng)
        seed = int(rng.integers(0, 2**31 - 1))
        data = generate_synthetic_data(
            n_samples=design["n_samples"],
            noise_std=design["noise_std"],
            seed=seed,
            signal=signal,
            signal_strength=signal_strength,
            x_range=(design["x_min"], design["x_max"]),
        )

        x_train, y_train, x_test, y_test = split_train_test(data.x, data.y, train_fraction=0.5)
        stats_out = evaluate_candidate(candidate, x_train, y_train, x_test, y_test)
        min_p = min(min_p, stats_out["p_value"])

        increments = prepare_candidate_increment_stream(
            candidate,
            x=data.x,
            y=data.y,
            train_fraction=0.4,
            clip_bound=2.0,
        )["increments"]
        e_test = run_grid_e_test(
            increments=np.asarray(increments, dtype=float),
            alpha_epoch=alpha,
            n_candidates=n_designs,
            stop_on_threshold=False,
        )
        max_e = max(max_e, e_test.final_e_value)

    threshold = n_designs / alpha
    return {
        "min_p_value": float(min_p),
        "max_e_value": float(max_e),
        "e_threshold": float(threshold),
    }


def run_simulation(
    n_runs: int = 350,
    design_counts: Iterable[int] = (5, 10, 25, 50),
    alpha: float = 0.05,
    alt_signal_strength: float = 0.35,
    seed: int = 2027,
    output_path: str | None = None,
) -> Dict[str, object]:
    rng = np.random.default_rng(seed)
    rows: List[Dict[str, float]] = []

    for n_designs in design_counts:
        null_naive = 0
        null_bonf = 0
        null_eproc = 0
        alt_naive = 0
        alt_bonf = 0
        alt_eproc = 0

        for _ in range(n_runs):
            null_stats = _design_statistics(
                candidate_name="sin_1x",
                signal=False,
                signal_strength=0.0,
                n_designs=int(n_designs),
                alpha=alpha,
                rng=rng,
            )
            alt_stats = _design_statistics(
                candidate_name="sin_1x",
                signal=True,
                signal_strength=alt_signal_strength,
                n_designs=int(n_designs),
                alpha=alpha,
                rng=rng,
            )

            if null_stats["min_p_value"] < alpha:
                null_naive += 1
            if null_stats["min_p_value"] < alpha / n_designs:
                null_bonf += 1
            if null_stats["max_e_value"] >= null_stats["e_threshold"]:
                null_eproc += 1

            if alt_stats["min_p_value"] < alpha:
                alt_naive += 1
            if alt_stats["min_p_value"] < alpha / n_designs:
                alt_bonf += 1
            if alt_stats["max_e_value"] >= alt_stats["e_threshold"]:
                alt_eproc += 1

        null_naive_ci = wilson_interval(null_naive, n_runs)
        null_bonf_ci = wilson_interval(null_bonf, n_runs)
        null_eproc_ci = wilson_interval(null_eproc, n_runs)
        alt_naive_ci = wilson_interval(alt_naive, n_runs)
        alt_bonf_ci = wilson_interval(alt_bonf, n_runs)
        alt_eproc_ci = wilson_interval(alt_eproc, n_runs)

        rows.append(
            {
                "n_designs": int(n_designs),
                "null_false_positive_rate_naive": null_naive_ci["rate"],
                "null_false_positive_rate_naive_ci_low": null_naive_ci["ci_low"],
                "null_false_positive_rate_naive_ci_high": null_naive_ci["ci_high"],
                "null_false_positive_rate_bonferroni": null_bonf_ci["rate"],
                "null_false_positive_rate_bonferroni_ci_low": null_bonf_ci["ci_low"],
                "null_false_positive_rate_bonferroni_ci_high": null_bonf_ci["ci_high"],
                "null_false_positive_rate_eprocess": null_eproc_ci["rate"],
                "null_false_positive_rate_eprocess_ci_low": null_eproc_ci["ci_low"],
                "null_false_positive_rate_eprocess_ci_high": null_eproc_ci["ci_high"],
                "alternative_detection_rate_naive": alt_naive_ci["rate"],
                "alternative_detection_rate_naive_ci_low": alt_naive_ci["ci_low"],
                "alternative_detection_rate_naive_ci_high": alt_naive_ci["ci_high"],
                "alternative_detection_rate_bonferroni": alt_bonf_ci["rate"],
                "alternative_detection_rate_bonferroni_ci_low": alt_bonf_ci["ci_low"],
                "alternative_detection_rate_bonferroni_ci_high": alt_bonf_ci["ci_high"],
                "alternative_detection_rate_eprocess": alt_eproc_ci["rate"],
                "alternative_detection_rate_eprocess_ci_low": alt_eproc_ci["ci_low"],
                "alternative_detection_rate_eprocess_ci_high": alt_eproc_ci["ci_high"],
            }
        )

    result: Dict[str, object] = {
        "simulation": "candidate_shopping",
        "alpha": alpha,
        "n_runs": n_runs,
        "confidence_level": 0.95,
        "alt_signal_strength": alt_signal_strength,
        "results_by_design_count": rows,
    }
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    data = run_simulation()
    print(json.dumps(data, indent=2))
