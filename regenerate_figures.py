"""Regenerate figures from an existing experiment results JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from results.plots import generate_all_plots


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Regenerate benchmark figures from a results JSON file.")
    parser.add_argument(
        "--input",
        default="results/experiment_results.json",
        help="Path to experiment results JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default="figures",
        help="Directory where figures will be written.",
    )
    return parser


if __name__ == "__main__":
    args = _build_cli().parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    files = generate_all_plots(payload, output_dir=args.output_dir)
    print(json.dumps(files, indent=2))
