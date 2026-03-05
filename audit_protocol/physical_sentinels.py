"""Hierarchical sentinel calibration logic for physical-coherence governance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SentinelThresholds:
    """Threshold contracts fixed by genesis for physical branch decisions."""

    spoof_threshold: float = 0.8
    primary_health_threshold: float = 0.7
    secondary_health_threshold: float = 0.7
    sensor_residual_threshold: float = 0.7
    secondary_primary_gap_threshold: float = 0.45


@dataclass(frozen=True)
class SentinelObservation:
    """Aggregated witness summary from fresh holdout runs."""

    primary_health_score: float
    secondary_health_score: float
    sensor_residual_score: float
    secondary_primary_gap: float
    spoof_score: float


@dataclass(frozen=True)
class SentinelDecision:
    """Audit branch decision for calibration update candidates."""

    branch: str
    action: str
    sensor_recalibration_allowed: bool
    sentinel_maintenance_required: bool
    admissible: bool
    rationale: str


def evaluate_hierarchical_sentinels(
    observation: SentinelObservation,
    thresholds: SentinelThresholds = SentinelThresholds(),
) -> SentinelDecision:
    """Evaluate sentinel hierarchy branch conditions.

    Branches:
    - spoofing: immediate escalation/reject.
    - sentinel_maintenance: primary/secondary sentinel maintenance path.
    - aging: sensor aging branch where recalibration may be allowed.
    - quarantine_review: ambiguous mixed signals.
    - healthy: no calibration change required.
    """
    if observation.spoof_score > thresholds.spoof_threshold:
        return SentinelDecision(
            branch="spoofing",
            action="reject_and_escalate",
            sensor_recalibration_allowed=False,
            sentinel_maintenance_required=True,
            admissible=False,
            rationale="spoof indicator exceeded threshold",
        )

    # Sentinel-collapse prevention rule: if primary checks fail, sensor recalibration is forbidden.
    if observation.primary_health_score > thresholds.primary_health_threshold:
        return SentinelDecision(
            branch="sentinel_maintenance",
            action="freeze_sensor_recalibration",
            sensor_recalibration_allowed=False,
            sentinel_maintenance_required=True,
            admissible=False,
            rationale="primary sentinel health failed",
        )

    secondary_bad = observation.secondary_health_score > thresholds.secondary_health_threshold
    sensor_bad = observation.sensor_residual_score > thresholds.sensor_residual_threshold
    gap_bad = observation.secondary_primary_gap > thresholds.secondary_primary_gap_threshold

    if sensor_bad and (not secondary_bad or not gap_bad):
        return SentinelDecision(
            branch="aging",
            action="recalibrate_sensor",
            sensor_recalibration_allowed=True,
            sentinel_maintenance_required=False,
            admissible=True,
            rationale="primary healthy and sensor-side drift indicated",
        )

    if secondary_bad and gap_bad and not sensor_bad:
        return SentinelDecision(
            branch="sentinel_maintenance",
            action="maintain_or_replace_secondary_sentinel",
            sensor_recalibration_allowed=False,
            sentinel_maintenance_required=True,
            admissible=False,
            rationale="secondary vs primary mismatch indicates sentinel-side drift",
        )

    if sensor_bad and secondary_bad and gap_bad:
        return SentinelDecision(
            branch="quarantine_review",
            action="collect_disjoint_holdout_and_retest",
            sensor_recalibration_allowed=False,
            sentinel_maintenance_required=True,
            admissible=False,
            rationale="mixed sensor/sentinel drift signals require quarantine",
        )

    return SentinelDecision(
        branch="healthy",
        action="no_calibration_update",
        sensor_recalibration_allowed=False,
        sentinel_maintenance_required=False,
        admissible=True,
        rationale="all physical checks within tolerance",
    )


def sentinel_decision_to_log_payload(
    decision: SentinelDecision,
    observation: SentinelObservation,
    thresholds: SentinelThresholds,
) -> Dict[str, object]:
    """Serialize sentinel decision details for transparency-log transcripts."""
    return {
        "branch": decision.branch,
        "action": decision.action,
        "sensor_recalibration_allowed": decision.sensor_recalibration_allowed,
        "sentinel_maintenance_required": decision.sentinel_maintenance_required,
        "admissible": decision.admissible,
        "rationale": decision.rationale,
        "observation": {
            "primary_health_score": observation.primary_health_score,
            "secondary_health_score": observation.secondary_health_score,
            "sensor_residual_score": observation.sensor_residual_score,
            "secondary_primary_gap": observation.secondary_primary_gap,
            "spoof_score": observation.spoof_score,
        },
        "thresholds": {
            "spoof_threshold": thresholds.spoof_threshold,
            "primary_health_threshold": thresholds.primary_health_threshold,
            "secondary_health_threshold": thresholds.secondary_health_threshold,
            "sensor_residual_threshold": thresholds.sensor_residual_threshold,
            "secondary_primary_gap_threshold": thresholds.secondary_primary_gap_threshold,
        },
    }
