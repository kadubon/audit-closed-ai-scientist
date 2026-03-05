"""Run all simulations and benchmarks for the audit-closed AI scientist repository."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import time
from typing import Any, Dict

import numpy as np
import scipy

from benchmarks.discovery_validity_benchmark import run_benchmark
from results.plots import generate_all_plots
from simulations.adversarial_agents import run_simulation as run_adversarial_simulation
from simulations.candidate_shopping import run_simulation as run_candidate_shopping_simulation
from simulations.certificate_schema_validation import run_simulation as run_certificate_schema_validation_simulation
from simulations.drift_localization_simulation import run_simulation as run_drift_localization_simulation
from simulations.optional_stopping import run_simulation as run_optional_stopping_simulation
from simulations.p_hacking_simulation import run_simulation as run_p_hacking_simulation
from simulations.power_curve import run_simulation as run_power_curve_simulation
from simulations.sentinel_hierarchy import run_simulation as run_sentinel_hierarchy_simulation


def _sha256_file(path: str | Path) -> str:
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _code_manifest() -> Dict[str, str]:
    tracked = [
        "run_all_experiments.py",
        "audit_protocol/transparency_log.py",
        "audit_protocol/audit_closed_update.py",
        "audit_protocol/e_process.py",
        "audit_protocol/sequential_tests.py",
        "baseline_ai_scientist/naive_scientist.py",
        "baseline_ai_scientist/experiment_runner.py",
        "simulations/p_hacking_simulation.py",
        "simulations/candidate_shopping.py",
        "simulations/optional_stopping.py",
        "simulations/power_curve.py",
        "simulations/sentinel_hierarchy.py",
        "simulations/drift_localization_simulation.py",
        "simulations/certificate_schema_validation.py",
        "simulations/adversarial_agents.py",
        "benchmarks/api.py",
        "benchmarks/discovery_validity_benchmark.py",
        "results/plots.py",
        "audit_protocol/physical_sentinels.py",
        "audit_protocol/drift_localization.py",
        "audit_protocol/certificate_schema.py",
        "paper/audit_closed_ai_scientist_protocol.tex",
    ]
    return {path: _sha256_file(path) for path in tracked if Path(path).exists()}


def _default_config_for_profile(profile: str) -> Path:
    config_path = Path("configs") / f"{profile}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"default config does not exist for profile={profile}: {config_path}")
    return config_path


def _load_run_config(profile: str, config_path: str | None) -> Dict[str, Any]:
    path = Path(config_path) if config_path else _default_config_for_profile(profile)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    loaded["_config_path"] = str(path.as_posix())
    loaded["_config_sha256"] = _sha256_file(path)
    return loaded


def run_all(
    output_path: str = "results/experiment_results.json",
    profile: str = "standard",
    config_path: str | None = None,
) -> Dict[str, object]:
    start = time.time()
    if profile not in {"quick", "standard"}:
        raise ValueError("profile must be 'quick' or 'standard'")

    cfg = _load_run_config(profile=profile, config_path=config_path)
    alpha = float(cfg["alpha"])
    seeds: Dict[str, int] = {k: int(v) for k, v in cfg["seeds"].items()}
    sizes: Dict[str, int] = {k: int(v) for k, v in cfg["sample_sizes"].items()}
    grids: Dict[str, list] = cfg["grids"]
    settings: Dict[str, Any] = cfg["settings"]

    results: Dict[str, object] = {}
    results["p_hacking_simulation"] = run_p_hacking_simulation(
        hypothesis_counts=tuple(int(x) for x in grids["hypothesis_counts"]),
        n_runs=sizes["p_hacking_runs"],
        alpha=alpha,
        seed=seeds["p_hacking"],
    )
    results["candidate_shopping"] = run_candidate_shopping_simulation(
        n_runs=sizes["candidate_shopping_runs"],
        design_counts=tuple(int(x) for x in grids["design_counts"]),
        alpha=alpha,
        alt_signal_strength=float(settings["candidate_alt_signal_strength"]),
        seed=seeds["candidate_shopping"],
    )
    results["optional_stopping"] = run_optional_stopping_simulation(
        alpha=alpha,
        max_looks_grid=tuple(int(x) for x in grids["max_looks_grid"]),
        n_runs_null=sizes["optional_null_runs"],
        n_runs_alt=sizes["optional_alt_runs"],
        alt_mean_shift=float(settings["optional_alt_mean_shift"]),
        seed=seeds["optional_stopping"],
    )
    results["power_curve"] = run_power_curve_simulation(
        effect_sizes=tuple(float(x) for x in grids["power_effect_sizes"]),
        n_runs=sizes["power_curve_runs"],
        max_looks=int(settings["power_max_looks"]),
        alpha=alpha,
        seed=seeds["power_curve"],
    )
    results["adversarial_agents"] = run_adversarial_simulation(
        malicious_counts=(0, 5, 20, 50, 100),
        n_runs=sizes["adversarial_runs"],
        honest_count=int(settings["adversarial_honest_count"]),
        fabricated_fraction=float(settings["adversarial_fabricated_fraction"]),
        alpha=alpha,
        seed=seeds["adversarial_agents"],
    )
    results["sentinel_hierarchy"] = run_sentinel_hierarchy_simulation(
        n_runs=sizes["sentinel_hierarchy_runs"],
        seed=seeds["sentinel_hierarchy"],
    )
    results["drift_localization"] = run_drift_localization_simulation(
        n_runs=sizes["drift_localization_runs"],
        n_subgraphs=int(settings["drift_subgraphs"]),
        alpha_drift=float(settings["drift_alpha"]),
        seed=seeds["drift_localization"],
    )
    results["certificate_schema_validation"] = run_certificate_schema_validation_simulation(
        n_valid=sizes["certificate_valid_runs"],
        n_invalid=sizes["certificate_invalid_runs"],
        seed=seeds["certificate_schema_validation"],
    )
    results["benchmark"] = run_benchmark(
        n_runs=sizes["benchmark_runs"],
        seed=seeds["benchmark"],
    )

    results["generated_figures"] = generate_all_plots(results, output_dir="figures")
    results["reproducibility"] = {
        "profile": profile,
        "config_path": cfg["_config_path"],
        "config_sha256": cfg["_config_sha256"],
        "seed_registry": seeds,
        "sample_sizes": sizes,
        "runtime_seconds": float(time.time() - start),
        "python": platform.python_version(),
        "os": platform.system(),
        "architecture": platform.machine(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "code_sha256_manifest": _code_manifest(),
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the full audit-closed benchmark suite.")
    parser.add_argument(
        "--profile",
        default="standard",
        choices=["quick", "standard"],
        help="Configuration profile name.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Optional JSON config path; overrides default configs/<profile>.json.",
    )
    parser.add_argument(
        "--output",
        default="results/experiment_results.json",
        help="Path to output JSON manifest.",
    )
    return parser


if __name__ == "__main__":
    args = _build_cli().parse_args()
    payload = run_all(output_path=args.output, profile=args.profile, config_path=args.config)
    print("Completed all experiments.")
    print(f"Results written to: {args.output}")
    print(f"Figures written to: {payload['generated_figures']}")
