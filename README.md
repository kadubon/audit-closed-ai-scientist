# audit-closed-ai-scientist

Audit-Closed AI Scientist is a benchmark for evaluating the statistical validity of autonomous research systems.

The repository demonstrates failure modes of naive AI scientist pipelines (p-hacking, optional stopping, hypothesis shopping) and provides a reproducible implementation of an audit-closed protocol based on transparency logs and sequential e-process inference.

This benchmark is intended for developers of AI scientist systems, autonomous research agents, and self-driving laboratories.

It is designed for:
- AI scientist developers
- autonomous research agents
- automated scientific discovery pipelines
- self-driving laboratories
- agentic AI research frameworks

The benchmark studies where naive autonomous discovery fails, and how an audit-closed protocol mitigates those failures using:
- transparency logs
- deterministic replay
- sequential e-process inference
- explicit alpha accounting

## Why this benchmark exists

Naive autonomous research loops are statistically unsafe under adaptive search. In this benchmark, naive pipelines are stress-tested under:
- optional stopping
- p-hacking / many-hypothesis search
- candidate and design shopping
- adversarial experiment submissions

The benchmark compares:
- naive discovery policies (publish when significance appears)
- audit-closed policies (`Accept_t = f(Log_0:t)`)

## Reference paper

- Takahashi, K. (2026). *Audit-Closed AI Scientist Protocol*. Zenodo. https://doi.org/10.5281/zenodo.18728589
- Repository manuscript: [`paper/audit_closed_ai_scientist_protocol.tex`](paper/audit_closed_ai_scientist_protocol.tex)

## What is implemented

Core simulations:
1. `simulations/p_hacking_simulation.py`
2. `simulations/candidate_shopping.py`
3. `simulations/optional_stopping.py`
4. `simulations/power_curve.py`
5. `simulations/adversarial_agents.py`

Protocol-extension benchmark modules:
1. `audit_protocol/physical_sentinels.py` + `simulations/sentinel_hierarchy.py`
2. `audit_protocol/drift_localization.py` + `simulations/drift_localization_simulation.py`
3. `audit_protocol/certificate_schema.py` + `simulations/certificate_schema_validation.py`

Integrated benchmark:
- `benchmarks/discovery_validity_benchmark.py`
  - false discovery rate
  - replication success
  - sequential evidence stability
  - adversarial robustness

## Reproduce results

### Pip

```bash
git clone https://github.com/kadubon/audit-closed-ai-scientist
cd audit-closed-ai-scientist
python -m pip install -r requirements.txt
python run_all_experiments.py --profile standard
```

### Conda

```bash
conda env create -f environment.yml
conda activate audit-closed-ai-scientist
python run_all_experiments.py --profile standard
```

### Make targets

```bash
make reproduce
make benchmark
make figures
make test
```

Output artifacts:
- `results/experiment_results.json`
- `figures/*.png`
- `result_summary.md`

Figure regeneration from raw JSON:

```bash
python regenerate_figures.py --input results/experiment_results.json --output-dir figures
```

## External agent API

Use the benchmark as an evaluation harness for your own AI scientist:

```python
from benchmarks import benchmark

# my_ai_scientist: callable or object with evaluate_trial(...)
report = benchmark.evaluate(my_ai_scientist)
print(report["null_world"]["false_discovery_rate"])
print(report["signal_world"]["replication_probability"])
```

Adapter contract (minimum return fields):
- `accepted: bool`
- `winner: str | None`

See [`docs/integration_with_ai_scientist_systems.md`](docs/integration_with_ai_scientist_systems.md).

## Security and audit integrity

Implemented safeguards:
- append-only hash-chained transparency log
- Merkle checkpoint verification
- fail-closed transcript checks
- candidate-set commitment before evaluation
- deterministic replay validation
- tamper tests for payload/hash/commitment/alpha rewrites

Security tests:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Scientific integrity statement

This repository is a benchmark-focused implementation.
It supports benchmark-level claims about statistical governance and replayability.
It does not claim full deployment implementation of all physical protocol components in the paper.

Detailed audits:
- [`docs/paper_alignment_audit.md`](docs/paper_alignment_audit.md)
- [`docs/security_audit.md`](docs/security_audit.md)
- [`docs/reproducibility.md`](docs/reproducibility.md)
- [`docs/repository_audit_report.md`](docs/repository_audit_report.md)
- [`result_summary.md`](result_summary.md)


## Citation

Software (repository DOI):
- Takahashi, K. (2026). *audit-closed-ai-scientist* (v0.1.0). Zenodo. https://doi.org/10.5281/zenodo.18870261

Protocol paper:
- Takahashi, K. (2026). *Audit-Closed AI Scientist Protocol*. Zenodo. https://doi.org/10.5281/zenodo.18728589

Machine-readable metadata is in [`CITATION.cff`](CITATION.cff).
