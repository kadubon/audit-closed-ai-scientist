"""Sentinel hierarchy stress test for calibration-collapse prevention."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import numpy as np

from audit_protocol.physical_sentinels import (
    SentinelObservation,
    SentinelThresholds,
    evaluate_hierarchical_sentinels,
)
from simulations.stat_utils import wilson_interval


def _observation_from_latent(
    sensor_aging: bool,
    secondary_aging: bool,
    primary_fail: bool,
    spoof_attack: bool,
    rng: np.random.Generator,
) -> SentinelObservation:
    primary = max(0.0, rng.normal(0.28, 0.09) + (0.85 if primary_fail else 0.0))
    secondary = max(
        0.0,
        rng.normal(0.28, 0.09) + (0.75 if secondary_aging else 0.0) + (0.35 if primary_fail else 0.0),
    )
    sensor_resid = max(0.0, rng.normal(0.25, 0.1) + (0.8 if sensor_aging else 0.0))
    gap = max(0.0, abs(secondary - primary) + (0.35 if secondary_aging else 0.0))
    spoof = max(0.0, rng.normal(0.2, 0.08) + (1.0 if spoof_attack else 0.0))
    return SentinelObservation(
        primary_health_score=float(primary),
        secondary_health_score=float(secondary),
        sensor_residual_score=float(sensor_resid),
        secondary_primary_gap=float(gap),
        spoof_score=float(spoof),
    )


def _single_sentinel_baseline_decision(
    observation: SentinelObservation,
    thresholds: SentinelThresholds,
) -> Dict[str, bool]:
    if observation.spoof_score > thresholds.spoof_threshold:
        return {"recalibrate_sensor": False, "freeze": True, "spoof_detected": True}
    recalibrate = max(observation.sensor_residual_score, observation.secondary_health_score) > thresholds.sensor_residual_threshold
    return {"recalibrate_sensor": recalibrate, "freeze": False, "spoof_detected": False}


def run_simulation(
    n_runs: int = 2500,
    seed: int = 2032,
    thresholds: SentinelThresholds = SentinelThresholds(),
    output_path: str | None = None,
) -> Dict[str, object]:
    rng = np.random.default_rng(seed)

    false_recal_single = 0
    false_recal_hier = 0
    freeze_single = 0
    freeze_hier = 0
    spoof_detect_single = 0
    spoof_detect_hier = 0
    spoof_total = 0

    for _ in range(n_runs):
        sensor_aging = bool(rng.random() < 0.28)
        secondary_aging = bool(rng.random() < 0.22)
        primary_fail = bool(rng.random() < 0.06)
        spoof_attack = bool(rng.random() < 0.05)
        if spoof_attack:
            spoof_total += 1

        obs = _observation_from_latent(
            sensor_aging=sensor_aging,
            secondary_aging=secondary_aging,
            primary_fail=primary_fail,
            spoof_attack=spoof_attack,
            rng=rng,
        )

        single = _single_sentinel_baseline_decision(observation=obs, thresholds=thresholds)
        hier = evaluate_hierarchical_sentinels(observation=obs, thresholds=thresholds)

        if single["freeze"]:
            freeze_single += 1
        if hier.branch in {"spoofing", "sentinel_maintenance", "quarantine_review"}:
            freeze_hier += 1

        if single["spoof_detected"] and spoof_attack:
            spoof_detect_single += 1
        if hier.branch == "spoofing" and spoof_attack:
            spoof_detect_hier += 1

        sentinel_issue = secondary_aging or primary_fail
        if single["recalibrate_sensor"] and (not sensor_aging) and sentinel_issue:
            false_recal_single += 1
        if hier.action == "recalibrate_sensor" and (not sensor_aging) and sentinel_issue:
            false_recal_hier += 1

    false_single_ci = wilson_interval(false_recal_single, n_runs)
    false_hier_ci = wilson_interval(false_recal_hier, n_runs)
    freeze_single_ci = wilson_interval(freeze_single, n_runs)
    freeze_hier_ci = wilson_interval(freeze_hier, n_runs)
    spoof_single_ci = wilson_interval(spoof_detect_single, max(spoof_total, 1))
    spoof_hier_ci = wilson_interval(spoof_detect_hier, max(spoof_total, 1))

    result: Dict[str, object] = {
        "simulation": "sentinel_hierarchy",
        "n_runs": n_runs,
        "confidence_level": 0.95,
        "spoof_total": int(spoof_total),
        "single_sentinel": {
            "false_sensor_recalibration_rate": false_single_ci["rate"],
            "false_sensor_recalibration_rate_ci_low": false_single_ci["ci_low"],
            "false_sensor_recalibration_rate_ci_high": false_single_ci["ci_high"],
            "operational_freeze_rate": freeze_single_ci["rate"],
            "spoof_detection_rate": spoof_single_ci["rate"],
        },
        "hierarchical_sentinels": {
            "false_sensor_recalibration_rate": false_hier_ci["rate"],
            "false_sensor_recalibration_rate_ci_low": false_hier_ci["ci_low"],
            "false_sensor_recalibration_rate_ci_high": false_hier_ci["ci_high"],
            "operational_freeze_rate": freeze_hier_ci["rate"],
            "spoof_detection_rate": spoof_hier_ci["rate"],
        },
    }
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    payload = run_simulation()
    print(json.dumps(payload, indent=2))
