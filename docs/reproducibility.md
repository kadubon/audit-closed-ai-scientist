# Reproducibility Guide

## Clean-environment reproduction

```bash
git clone <repo-url>
cd audit-closed-ai-scientist
python -m pip install -r requirements.txt
python run_all_experiments.py --profile standard
```

Outputs:
- `results/experiment_results.json`
- regenerated figures in `figures/`

## Conda reproduction

```bash
conda env create -f environment.yml
conda activate audit-closed-ai-scientist
python run_all_experiments.py --profile standard
```

## Make targets

```bash
make reproduce
make benchmark
make figures
make test
```

- `make reproduce`: full standard benchmark suite.
- `make benchmark`: integrated benchmark only.
- `make figures`: regenerate figures from existing JSON output.
- `make test`: protocol/security tests.
- Note: these targets require `make` (GNU Make compatible).

## Configuration files

Run profiles are backed by explicit config files:
- `configs/quick.json`
- `configs/standard.json`

You can provide a custom config:

```bash
python run_all_experiments.py --profile standard --config configs/standard.json
```

## Determinism conventions

- Each simulation has explicit seeds recorded in output JSON (`reproducibility.seed_registry`).
- Sample sizes are recorded in `reproducibility.sample_sizes`.
- Config file SHA-256 is recorded in `reproducibility.config_sha256`.
- Core source-file SHA-256 manifest is recorded in `reproducibility.code_sha256_manifest`.

## Figure regeneration

Use existing results JSON:

```bash
python regenerate_figures.py --input results/experiment_results.json --output-dir figures
```
