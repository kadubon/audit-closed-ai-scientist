"""Adversarial-agent simulation: fabrication, spam, and log tampering attacks."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np

from audit_protocol.audit_closed_update import acceptance_from_public_log
from audit_protocol.sequential_tests import AlphaSpendingSchedule, run_grid_e_test
from audit_protocol.transparency_log import TransparencyLog
from baseline_ai_scientist.experiment_runner import one_sided_mean_positive_pvalue
from simulations.stat_utils import wilson_interval


def _null_candidate_pvalue(rng: np.random.Generator, n_samples: int = 70) -> float:
    samples = rng.normal(loc=0.0, scale=1.0, size=n_samples)
    p_value, _ = one_sided_mean_positive_pvalue(samples)
    return float(p_value)


def _null_candidate_evalue(rng: np.random.Generator, n_samples: int = 90) -> float:
    samples = rng.normal(loc=0.0, scale=1.0, size=n_samples)
    increments = np.clip(samples / 3.0, -1.0, 1.0)
    test = run_grid_e_test(
        increments=np.asarray(increments, dtype=float),
        alpha_epoch=0.05,
        n_candidates=1,
        stop_on_threshold=False,
    )
    return float(test.final_e_value)


def _tamper_payload(log: TransparencyLog) -> Dict[str, object]:
    payload = {"integrity_ok": log.verify_integrity(), "entries": log.to_serializable(), "checkpoint": log.checkpoint()}
    tampered = copy.deepcopy(payload)
    if len(tampered["entries"]) > 2:
        tampered["entries"][2]["payload"]["final_e_value"] = 1e9
    is_detected = not TransparencyLog.verify_serialized_payload(tampered)
    return {"detected": bool(is_detected)}


def _single_attack_trial(
    malicious_count: int,
    honest_count: int,
    fabricated_fraction: float,
    alpha: float,
    rng: np.random.Generator,
) -> Dict[str, object]:
    spam_count = int(round(malicious_count * (1.0 - fabricated_fraction)))
    fabricated_count = malicious_count - spam_count

    baseline_pvalues: List[float] = []
    for _ in range(honest_count + spam_count):
        baseline_pvalues.append(_null_candidate_pvalue(rng))
    for _ in range(fabricated_count):
        baseline_pvalues.append(float(rng.uniform(1e-12, 1e-4)))
    baseline_accept = bool(np.min(baseline_pvalues) < alpha)

    # total_alpha=2*alpha with decay=0.5 gives epoch-0 budget alpha.
    total_alpha = 2.0 * alpha
    alpha_decay = 0.5

    log = TransparencyLog()
    log.append(
        "genesis",
        {
            "total_alpha": total_alpha,
            "alpha_decay": alpha_decay,
            "attack_model": "fabrication_plus_spam",
        },
    )

    committed_names = [f"honest_{idx}" for idx in range(honest_count)] + [
        f"spam_{idx}" for idx in range(spam_count)
    ]
    alpha_epoch = AlphaSpendingSchedule(total_alpha=total_alpha, decay=alpha_decay).alpha_for_epoch(0)
    batch_threshold = len(committed_names) / alpha_epoch
    log.append(
        "candidate_commitment",
        {
            "epoch": 0,
            "candidate_names": committed_names,
        },
    )

    for name in committed_names:
        log.append(
            "candidate_evaluation",
            {
                "epoch": 0,
                "candidate_name": name,
                "final_e_value": _null_candidate_evalue(rng),
                "alpha_epoch": float(alpha_epoch),
                "batch_threshold": float(batch_threshold),
            },
        )
    for idx in range(fabricated_count):
        log.append(
            "integrity_reject",
            {
                "epoch": 0,
                "submission_id": f"fabricated_{idx}",
                "reason": "missing_attested_measurement_record",
            },
        )

    audit_decision = acceptance_from_public_log(
        log_entries=log.entries,
        epoch=0,
        total_alpha=total_alpha,
        alpha_decay=alpha_decay,
    )
    replay_decision = acceptance_from_public_log(
        log_entries=log.entries,
        epoch=0,
        total_alpha=total_alpha,
        alpha_decay=alpha_decay,
    )
    tamper_detection = _tamper_payload(log)

    return {
        "baseline_accept": baseline_accept,
        "audit_accept": bool(audit_decision["accepted"]),
        "replay_match": bool(audit_decision == replay_decision),
        "log_integrity_ok": log.verify_integrity(),
        "tamper_detection": tamper_detection["detected"],
        "fabricated_count": fabricated_count,
        "spam_count": spam_count,
    }


def run_simulation(
    malicious_counts: Iterable[int] = (0, 5, 20, 50, 100),
    n_runs: int = 500,
    honest_count: int = 10,
    fabricated_fraction: float = 0.35,
    alpha: float = 0.05,
    seed: int = 2029,
    output_path: str | None = None,
) -> Dict[str, object]:
    rng = np.random.default_rng(seed)
    curve = []
    for malicious_count in malicious_counts:
        trial_data = [
            _single_attack_trial(
                malicious_count=int(malicious_count),
                honest_count=honest_count,
                fabricated_fraction=fabricated_fraction,
                alpha=alpha,
                rng=rng,
            )
            for _ in range(n_runs)
        ]

        baseline_count = int(np.sum([d["baseline_accept"] for d in trial_data]))
        audit_count = int(np.sum([d["audit_accept"] for d in trial_data]))
        replay_count = int(np.sum([d["replay_match"] for d in trial_data]))
        integrity_count = int(np.sum([d["log_integrity_ok"] for d in trial_data]))
        tamper_count = int(np.sum([d["tamper_detection"] for d in trial_data]))

        baseline_ci = wilson_interval(baseline_count, n_runs)
        audit_ci = wilson_interval(audit_count, n_runs)
        replay_ci = wilson_interval(replay_count, n_runs)
        integrity_ci = wilson_interval(integrity_count, n_runs)
        tamper_ci = wilson_interval(tamper_count, n_runs)

        curve.append(
            {
                "malicious_candidates": int(malicious_count),
                "baseline_false_accept_rate": baseline_ci["rate"],
                "baseline_false_accept_rate_ci_low": baseline_ci["ci_low"],
                "baseline_false_accept_rate_ci_high": baseline_ci["ci_high"],
                "audit_false_accept_rate": audit_ci["rate"],
                "audit_false_accept_rate_ci_low": audit_ci["ci_low"],
                "audit_false_accept_rate_ci_high": audit_ci["ci_high"],
                "replay_match_rate": replay_ci["rate"],
                "log_integrity_pass_rate": integrity_ci["rate"],
                "tamper_detection_rate": tamper_ci["rate"],
            }
        )

    result: Dict[str, object] = {
        "simulation": "adversarial_agents",
        "alpha": alpha,
        "n_runs": n_runs,
        "confidence_level": 0.95,
        "honest_count": honest_count,
        "fabricated_fraction": fabricated_fraction,
        "robustness_curve": curve,
    }
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    data = run_simulation()
    print(json.dumps(data, indent=2))
