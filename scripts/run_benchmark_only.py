"""Run only the integrated benchmark and write a JSON artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.discovery_validity_benchmark import run_benchmark


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run only the integrated benchmark.")
    parser.add_argument("--runs", type=int, default=320, help="Number of Monte Carlo benchmark runs.")
    parser.add_argument("--seed", type=int, default=2030, help="Random seed.")
    parser.add_argument(
        "--output",
        default="results/benchmark_only.json",
        help="Output JSON path.",
    )
    return parser


if __name__ == "__main__":
    args = _build_cli().parse_args()
    result = run_benchmark(n_runs=args.runs, seed=args.seed)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote benchmark results to: {path.as_posix()}")
