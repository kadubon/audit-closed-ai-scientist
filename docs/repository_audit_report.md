# Repository Audit Report

Date: 2026-03-05  
Scope: statistical validity, protocol alignment, security, reproducibility, and usability

## 1) Paper alignment audit

### Findings (before improvements)
- Acceptance logic did not fail closed on malformed logs (missing/duplicate candidate evaluations).
- Transparency log lacked root-level checkpointing and serialization-level integrity verification.
- Alpha/accounting values were accepted as function arguments instead of being strictly anchored to logged genesis values.

### Implemented corrections
- Added fail-closed log validation in `acceptance_from_public_log`:
  - single commitment per epoch
  - unique candidate names
  - no uncommitted evaluations
  - no duplicate evaluations
  - no missing evaluations
- Anchored alpha schedule to logged genesis values with mismatch rejection.
- Added Merkle-root checkpoint support and serialized payload verification in `TransparencyLog`.
- Added detailed paper-to-code mapping in `docs/paper_alignment_audit.md`.

## 2) Scientific validity audit

### Findings (before improvements)
- Simulations lacked uncertainty quantification.
- Candidate-shopping output was single-point and under-informative.
- Optional-stopping comparison missed fixed-horizon control reference.
- Benchmark baseline/audit comparison was not budget-matched.

### Implemented corrections
- Added Wilson confidence intervals across all major rate metrics.
- Redesigned candidate-shopping simulation across multiple design counts.
- Added fixed-horizon p-value baseline in optional-stopping simulation.
- Added power-curve simulation across effect sizes (`simulations/power_curve.py`).
- Rebuilt benchmark as budget-matched baseline vs audit-closed comparison.
- Added stronger p-hacking calibration (theory curve + Bonferroni reference).

## 3) Reproducibility audit

### Findings (before improvements)
- Missing conda environment specification.
- Runtime outputs lacked source hash manifest.

### Implemented corrections
- Added `environment.yml`.
- Pinned exact dependency versions in `requirements.txt`.
- Added external profile configs in `configs/*.json`.
- Extended `run_all_experiments.py` with:
  - quick/standard profiles
  - config loading + config hash recording
  - seed registry
  - sample-size manifest
  - SHA-256 code manifest
- Added `Makefile` and `regenerate_figures.py` for scripted reproduction.
- Added reproducibility documentation.

## 4) Security audit

### Findings (before improvements)
- Hash chain only; no root checkpoint verification path.
- Replay integrity checks did not fully guard against malformed epoch transcripts.

### Implemented corrections
- Added Merkle checkpoints and serialized payload verification.
- Added optional HMAC checkpoint signature support for witness anchoring.
- Added adversarial tamper test and tamper-detection metric.
- Added unit tests for tampering/fail-closed behavior (`tests/test_security_audit_protocol.py`).
- Added security audit documentation and operational recommendations.

## 5) Benchmark clarity and usability

### Implemented corrections
- Added candidate-shopping visualization.
- Added power-curve visualization.
- Added optional-stopping calibration deviation visualization.
- Added sentinel-hierarchy and drift-localization simulations.
- Added certificate-schema validation simulation.
- Added API layer (`benchmarks/api.py`) for external integration, including:
  - `benchmarks.benchmark.evaluate(my_ai_scientist)`
  - `DiscoveryValidityHarness` for adapter-driven evaluation
- Added integration guide for AI scientist frameworks.
- Added package exports in `audit_protocol`, `baseline_ai_scientist`, and `simulations`.

## 6) Research impact positioning

### Outcome
The repository now more clearly occupies a benchmark gap:
- trustworthy sequential inference for autonomous discovery
- audit-closed governance under adversarial and adaptive conditions
- reproducible, externally-checkable scientific update decisions

## 7) Protocol-extension implementation pass

### Implemented modules
- `audit_protocol/physical_sentinels.py`
- `audit_protocol/drift_localization.py`
- `audit_protocol/certificate_schema.py`

### Implemented extension simulations
- `simulations/sentinel_hierarchy.py`
- `simulations/drift_localization_simulation.py`
- `simulations/certificate_schema_validation.py`

### Added validation tests
- `tests/test_protocol_extensions.py`

### Scientific caution
These modules provide benchmark abstractions aligned with manuscript concepts, not full hardware-attested production implementations.

## 8) Public release hygiene pass

### Implemented corrections
- Removed cached bytecode artifacts (`__pycache__`) to avoid accidental local path leakage in public release bundles.
- Kept `.gitignore` aligned with generated artifact classes.
