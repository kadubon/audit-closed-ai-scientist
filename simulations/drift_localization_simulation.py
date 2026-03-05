"""Subgraph-local drift localization stress test."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import numpy as np

from audit_protocol.drift_localization import localize_drift_mode
from simulations.stat_utils import wilson_interval


def run_simulation(
    n_runs: int = 1500,
    n_subgraphs: int = 4,
    alpha_drift: float = 0.05,
    seed: int = 2033,
    output_path: str | None = None,
) -> Dict[str, object]:
    rng = np.random.default_rng(seed)

    unaffected_uptime_global = 0.0
    unaffected_uptime_localized = 0.0
    unaffected_slots = 0
    false_local_quarantine = 0
    affected_detected = 0
    global_trigger_count = 0

    for _ in range(n_runs):
        affected_idx = int(rng.integers(0, n_subgraphs))
        local_e_values = []
        for k in range(n_subgraphs):
            if k == affected_idx:
                # Positive drift signal.
                local_e = float(np.exp(rng.normal(np.log(130.0), 0.45)))
            else:
                # Null-like e-values with expectation below 1.
                local_e = float(np.exp(rng.normal(-0.9, 0.75)))
            local_e_values.append(local_e)

        global_e_value = float(np.max(local_e_values))
        decision = localize_drift_mode(
            global_e_value=global_e_value,
            local_e_values=local_e_values,
            alpha_drift=alpha_drift,
        )

        unaffected_indices = [k for k in range(n_subgraphs) if k != affected_idx]
        unaffected_slots += len(unaffected_indices)

        if decision.drift_triggered:
            global_trigger_count += 1
            # Global-freeze baseline quarantines all subgraphs.
            unaffected_uptime_global += 0.0

            exempted_unaffected = sum(1 for idx in unaffected_indices if idx in decision.exempted_subgraphs)
            unaffected_uptime_localized += exempted_unaffected / len(unaffected_indices)
            false_local_quarantine += len(unaffected_indices) - exempted_unaffected

            if affected_idx in decision.rejected_subgraphs:
                affected_detected += 1
        else:
            unaffected_uptime_global += 1.0
            unaffected_uptime_localized += 1.0

    false_local_ci = wilson_interval(false_local_quarantine, unaffected_slots)
    trigger_ci = wilson_interval(global_trigger_count, n_runs)
    affected_det_ci = wilson_interval(affected_detected, max(global_trigger_count, 1))

    result: Dict[str, object] = {
        "simulation": "drift_localization",
        "n_runs": n_runs,
        "n_subgraphs": n_subgraphs,
        "alpha_drift": alpha_drift,
        "confidence_level": 0.95,
        "global_trigger_rate": trigger_ci["rate"],
        "global_trigger_rate_ci_low": trigger_ci["ci_low"],
        "global_trigger_rate_ci_high": trigger_ci["ci_high"],
        "unaffected_subgraph_uptime_global_freeze": float(unaffected_uptime_global / n_runs),
        "unaffected_subgraph_uptime_localized_exemption": float(unaffected_uptime_localized / n_runs),
        "false_local_quarantine_rate": false_local_ci["rate"],
        "false_local_quarantine_rate_ci_low": false_local_ci["ci_low"],
        "false_local_quarantine_rate_ci_high": false_local_ci["ci_high"],
        "affected_subgraph_detection_rate": affected_det_ci["rate"],
        "affected_subgraph_detection_rate_ci_low": affected_det_ci["ci_low"],
        "affected_subgraph_detection_rate_ci_high": affected_det_ci["ci_high"],
    }
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    payload = run_simulation()
    print(json.dumps(payload, indent=2))
