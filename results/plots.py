"""Plotting utilities for audit-closed AI scientist benchmark results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import numpy as np


def _ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def plot_false_discoveries(results: Dict[str, object], output_dir: str | Path) -> Path:
    rows = results["p_hacking_simulation"]["false_discovery_rate_by_hypothesis_count"]
    x = np.asarray([row["n_hypotheses"] for row in rows], dtype=float)
    y = np.asarray([row["false_discovery_rate_naive"] for row in rows], dtype=float)
    y_bonf = np.asarray([row["false_discovery_rate_bonferroni"] for row in rows], dtype=float)
    y_theory = np.asarray([row["independent_null_theory_naive"] for row in rows], dtype=float)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x, y, marker="o", linewidth=2, color="#c44e52", label="Naive (min p < alpha)")
    ax.plot(x, y_bonf, marker="s", linewidth=2, color="#55a868", label="Bonferroni-corrected")
    ax.plot(x, y_theory, linestyle="--", linewidth=1.6, color="#000000", label="Theory: 1-(1-alpha)^m")
    ax.set_xscale("log")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("False Discoveries vs Number of Hypotheses")
    ax.set_xlabel("Number of Candidate Hypotheses (log scale)")
    ax.set_ylabel("False Discovery Rate (null world)")
    ax.grid(alpha=0.3, linestyle="--")
    ax.legend()
    out = _ensure_dir(output_dir) / "false_discoveries_vs_hypotheses.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_p_vs_e_reliability(results: Dict[str, object], output_dir: str | Path) -> Path:
    rows = results["optional_stopping"]["false_positive_by_max_looks"]
    looks = np.asarray([row["max_looks"] for row in rows], dtype=float)
    p_rate = np.asarray([row["p_value_false_positive_rate_peeking"] for row in rows], dtype=float)
    p_fixed = np.asarray([row["p_value_false_positive_rate_fixed_horizon"] for row in rows], dtype=float)
    e_rate = np.asarray([row["e_value_false_positive_rate_sequential"] for row in rows], dtype=float)
    alpha = float(results["optional_stopping"]["alpha"])

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(looks, p_rate, marker="o", linewidth=2, label="Naive p-value peeking", color="#dd8452")
    ax.plot(looks, p_fixed, marker="^", linewidth=2, label="P-value fixed horizon", color="#55a868")
    ax.plot(looks, e_rate, marker="s", linewidth=2, label="E-value sequential test", color="#4c72b0")
    ax.axhline(alpha, color="black", linestyle="--", linewidth=1.2, label=f"Nominal alpha={alpha:.2f}")
    ax.set_ylim(0.0, max(0.12, float(np.max(p_rate) * 1.1)))
    ax.set_title("P-value vs E-value Reliability Under Optional Stopping")
    ax.set_xlabel("Maximum Number of Looks")
    ax.set_ylabel("Null Crossing Rate")
    ax.grid(alpha=0.3, linestyle="--")
    ax.legend()
    out = _ensure_dir(output_dir) / "p_vs_e_reliability.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_optional_stopping_calibration(results: Dict[str, object], output_dir: str | Path) -> Path:
    rows = results["optional_stopping"]["false_positive_by_max_looks"]
    looks = np.asarray([row["max_looks"] for row in rows], dtype=float)
    alpha = float(results["optional_stopping"]["alpha"])
    p_peek = np.asarray([row["p_value_false_positive_rate_peeking"] for row in rows], dtype=float)
    p_fixed = np.asarray([row["p_value_false_positive_rate_fixed_horizon"] for row in rows], dtype=float)
    e_rate = np.asarray([row["e_value_false_positive_rate_sequential"] for row in rows], dtype=float)

    p_peek_dev = p_peek - alpha
    p_fixed_dev = p_fixed - alpha
    e_dev = e_rate - alpha

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(looks, p_peek_dev, marker="o", linewidth=2, color="#dd8452", label="Peeking p-value")
    ax.plot(looks, p_fixed_dev, marker="^", linewidth=2, color="#55a868", label="Fixed-horizon p-value")
    ax.plot(looks, e_dev, marker="s", linewidth=2, color="#4c72b0", label="Sequential e-value")
    ax.axhline(0.0, color="black", linestyle="--", linewidth=1.2)
    ax.set_title("Optional-Stopping Calibration Deviation")
    ax.set_xlabel("Maximum Number of Looks")
    ax.set_ylabel("Empirical null rate - nominal alpha")
    ax.grid(alpha=0.3, linestyle="--")
    ax.legend()
    out = _ensure_dir(output_dir) / "optional_stopping_calibration.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_candidate_shopping(results: Dict[str, object], output_dir: str | Path) -> Path:
    rows = results["candidate_shopping"]["results_by_design_count"]
    x = np.asarray([row["n_designs"] for row in rows], dtype=float)
    naive = np.asarray([row["null_false_positive_rate_naive"] for row in rows], dtype=float)
    bonf = np.asarray([row["null_false_positive_rate_bonferroni"] for row in rows], dtype=float)
    eproc = np.asarray([row["null_false_positive_rate_eprocess"] for row in rows], dtype=float)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x, naive, marker="o", linewidth=2, color="#dd8452", label="Naive min p")
    ax.plot(x, bonf, marker="^", linewidth=2, color="#55a868", label="Bonferroni")
    ax.plot(x, eproc, marker="s", linewidth=2, color="#4c72b0", label="E-process")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Candidate Shopping: False Discovery Inflation")
    ax.set_xlabel("Number of Candidate Designs Tried")
    ax.set_ylabel("Null False Positive Rate")
    ax.grid(alpha=0.3, linestyle="--")
    ax.legend()
    out = _ensure_dir(output_dir) / "candidate_shopping_false_discovery.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_replication_success(results: Dict[str, object], output_dir: str | Path) -> Path:
    repl = results["benchmark"]["replicability"]
    labels = ["Baseline", "Audit-Closed"]
    values = [
        float(repl["baseline_replication_success_rate"]),
        float(repl["audit_replication_success_rate"]),
    ]

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    bars = ax.bar(labels, values, color=["#dd8452", "#4c72b0"], width=0.6)
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Replication Success Rate")
    ax.set_ylabel("Replication Success Among Accepted Discoveries")
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2.0, value + 0.02, f"{value:.2f}", ha="center", va="bottom")
    out = _ensure_dir(output_dir) / "replication_success_rate.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_adversarial_robustness(results: Dict[str, object], output_dir: str | Path) -> Path:
    rows = results["adversarial_agents"]["robustness_curve"]
    x = np.asarray([row["malicious_candidates"] for row in rows], dtype=float)
    baseline = np.asarray([row["baseline_false_accept_rate"] for row in rows], dtype=float)
    audit = np.asarray([row["audit_false_accept_rate"] for row in rows], dtype=float)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x, baseline, marker="o", linewidth=2, label="Baseline", color="#dd8452")
    ax.plot(x, audit, marker="s", linewidth=2, label="Audit-Closed", color="#4c72b0")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Robustness to Adversarial Candidate Attacks")
    ax.set_xlabel("Number of Malicious Candidates")
    ax.set_ylabel("False Acceptance Rate")
    ax.grid(alpha=0.3, linestyle="--")
    ax.legend()
    out = _ensure_dir(output_dir) / "adversarial_robustness.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_power_curve(results: Dict[str, object], output_dir: str | Path) -> Path:
    rows = results["power_curve"]["rows"]
    x = np.asarray([row["effect_size"] for row in rows], dtype=float)
    p_peek = np.asarray([row["peeking_p_detection_rate"] for row in rows], dtype=float)
    p_fixed = np.asarray([row["fixed_p_detection_rate"] for row in rows], dtype=float)
    e_rate = np.asarray([row["e_value_detection_rate"] for row in rows], dtype=float)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x, p_peek, marker="o", linewidth=2, label="Peeking p-value", color="#dd8452")
    ax.plot(x, p_fixed, marker="^", linewidth=2, label="Fixed-horizon p-value", color="#55a868")
    ax.plot(x, e_rate, marker="s", linewidth=2, label="Sequential e-value", color="#4c72b0")
    ax.set_ylim(0.0, 1.0)
    ax.set_xlim(float(np.min(x)), float(np.max(x)))
    ax.set_title("Detection Power vs Effect Size")
    ax.set_xlabel("Effect Size (mean shift)")
    ax.set_ylabel("Detection Probability")
    ax.grid(alpha=0.3, linestyle="--")
    ax.legend()
    out = _ensure_dir(output_dir) / "power_curve_detection.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_sentinel_hierarchy(results: Dict[str, object], output_dir: str | Path) -> Path:
    single = results["sentinel_hierarchy"]["single_sentinel"]
    hier = results["sentinel_hierarchy"]["hierarchical_sentinels"]

    labels = ["False Sensor Recal", "Operational Freeze", "Spoof Detection"]
    single_vals = [
        float(single["false_sensor_recalibration_rate"]),
        float(single["operational_freeze_rate"]),
        float(single["spoof_detection_rate"]),
    ]
    hier_vals = [
        float(hier["false_sensor_recalibration_rate"]),
        float(hier["operational_freeze_rate"]),
        float(hier["spoof_detection_rate"]),
    ]

    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.bar(x - width / 2.0, single_vals, width=width, label="Single sentinel", color="#dd8452")
    ax.bar(x + width / 2.0, hier_vals, width=width, label="Hierarchical sentinels", color="#4c72b0")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Rate")
    ax.set_title("Sentinel Hierarchy Stress Test")
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.legend()
    out = _ensure_dir(output_dir) / "sentinel_hierarchy_stress.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def plot_drift_localization(results: Dict[str, object], output_dir: str | Path) -> Path:
    data = results["drift_localization"]
    labels = ["Global Freeze", "Localized Exemption"]
    uptime_vals = [
        float(data["unaffected_subgraph_uptime_global_freeze"]),
        float(data["unaffected_subgraph_uptime_localized_exemption"]),
    ]
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    bars = ax.bar(labels, uptime_vals, color=["#dd8452", "#4c72b0"], width=0.6)
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Unaffected Subgraph Uptime")
    ax.set_title("Drift Localization vs Global Freeze")
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    for bar, val in zip(bars, uptime_vals):
        ax.text(bar.get_x() + bar.get_width() / 2.0, val + 0.015, f"{val:.2f}", ha="center")
    out = _ensure_dir(output_dir) / "drift_localization_uptime.png"
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def generate_all_plots(
    results: Dict[str, object],
    output_dir: str | Path = "figures",
) -> Dict[str, str]:
    files = {
        "false_discoveries_vs_hypotheses": str(plot_false_discoveries(results, output_dir)),
        "candidate_shopping_false_discovery": str(plot_candidate_shopping(results, output_dir)),
        "p_vs_e_reliability": str(plot_p_vs_e_reliability(results, output_dir)),
        "optional_stopping_calibration": str(plot_optional_stopping_calibration(results, output_dir)),
        "power_curve_detection": str(plot_power_curve(results, output_dir)),
        "sentinel_hierarchy_stress": str(plot_sentinel_hierarchy(results, output_dir)),
        "drift_localization_uptime": str(plot_drift_localization(results, output_dir)),
        "replication_success_rate": str(plot_replication_success(results, output_dir)),
        "adversarial_robustness": str(plot_adversarial_robustness(results, output_dir)),
    }
    return files


if __name__ == "__main__":
    default_results_path = Path("results/experiment_results.json")
    if not default_results_path.exists():
        raise FileNotFoundError("results/experiment_results.json not found")
    payload = json.loads(default_results_path.read_text(encoding="utf-8"))
    outputs = generate_all_plots(payload, output_dir="figures")
    print(json.dumps(outputs, indent=2))
