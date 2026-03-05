# Paper Alignment Audit (Detailed)

Reference: Takahashi, K. (2026), *Audit-Closed AI Scientist Protocol*, DOI: 10.5281/zenodo.18728589

This audit checks whether the repository implementation matches the protocol concepts needed for the benchmark objective.

## Scope statement

The repository implements a **benchmark subset** of the paper, focused on:
- optional stopping validity
- many-candidate inflation
- candidate shopping
- adversarial submission pressure
- audit-closed deterministic decision replay
- hierarchical sentinel branch logic (benchmark abstraction)
- subgraph-local drift localization (benchmark abstraction)
- minimal incorporation-certificate schema validation

It does **not** implement the entire physical-world protocol stack (for example full sentinel hierarchy operations, drift-mode localization, and full hardware-attestation pipelines).

## Concept-to-implementation mapping

| Paper concept | Repository implementation | Status |
|---|---|---|
| `Accept_t = f(Log_0:t)` deterministic audit-closed rule | `audit_protocol/audit_closed_update.py::acceptance_from_public_log` | Implemented |
| Transparency log (append-only, tamper-evident) | `audit_protocol/transparency_log.py` hash chain + Merkle checkpoint + payload verification | Implemented (benchmark form) |
| Candidate commitment before evaluation | `candidate_commitment` events in `AuditClosedScientist.evaluate_epoch` | Implemented |
| Fail-closed transcript validation | Duplicate/missing/uncommitted evaluation checks in `acceptance_from_public_log` | Implemented |
| Sequential e-process inference | `audit_protocol/e_process.py` and `audit_protocol/sequential_tests.py` | Implemented |
| Optional stopping validity demonstration | `simulations/optional_stopping.py` | Implemented |
| Alpha accounting | `AlphaSpendingSchedule`, batch threshold `m/alpha_t` | Implemented |
| Adversarial failure-mode benchmark | `simulations/adversarial_agents.py` | Implemented |
| Deterministic replay | `AuditClosedScientist.replay_epoch` + integrity checks | Implemented |
| Physical attestation/sentinel hierarchy | `audit_protocol/physical_sentinels.py`, `simulations/sentinel_hierarchy.py` | Implemented (benchmark abstraction) |
| Drift localization closed testing | `audit_protocol/drift_localization.py`, `simulations/drift_localization_simulation.py` | Implemented (benchmark abstraction) |
| Minimal incorporation certificate schema | `audit_protocol/certificate_schema.py`, `simulations/certificate_schema_validation.py` | Implemented (schema-level) |
| Byzantine multi-agent evidence aggregation | Not benchmarked in code | Not implemented in this repo |

## Verification notes

### 1) Audit-closed rule
- Acceptance depends only on logged genesis config, commitment, and candidate evaluation events.
- Hidden runtime state is not used in decision replay.

### 2) Transparency and tamper detection
- Entry-level tampering breaks hash-chain verification.
- Serialization-level mutations are detected by checkpoint verification.
- Adversarial simulation explicitly tests post-hoc payload tampering.

### 3) Sequential validity
- Optional-stopping benchmark compares:
  - peeking p-values
  - fixed-horizon p-values
  - sequential e-values
- Observed results show peeking inflation and controlled e-value behavior under sequential stopping.

### 4) Alpha accounting
- Epoch alpha budget is computed via geometric spending.
- Batch multiplicity threshold follows `e >= m/alpha_t`.
- Decision function rejects mismatched alpha parameters against logged genesis.

## Deviations from full paper (honest disclosure)

This benchmark is a statistically focused implementation and does not claim full coverage of:
- physical provenance attestations and challenge nonces
- hardware-in-the-loop primary/secondary sentinel operations
- full root-memory erosion countermeasure pipeline
- full drift-mode transition and recovery controller
- complete certificate cryptographic attestation stack from the manuscript appendix

## Mismatch register and corrective actions

| Mismatch found during audit | Correction applied | File |
|---|---|---|
| Acceptance path did not cryptographically recompute entry hash at decision time | Added hash recomputation in chain verification (`expected_entry_hash`) | `audit_protocol/audit_closed_update.py` |
| Candidate evaluation transcript could omit gate accounting fields | `alpha_epoch` and `batch_threshold` are now required and checked | `audit_protocol/audit_closed_update.py` |
| Profile parameters lived in code constants only | Added external config files with recorded config SHA-256 | `configs/*.json`, `run_all_experiments.py` |
| Security checks were simulation-only | Added executable protocol tampering tests | `tests/test_security_audit_protocol.py` |
| Sentinel/drift/schema blocks were only documented | Added executable benchmark modules and simulations | `audit_protocol/*.py`, `simulations/*.py` |

## Recommended next alignment steps

1. Extend sentinel module with explicit attestation nonce/signature lifecycle.
2. Extend drift module with root-memory erosion (`m_ext`, `kappa_t`) dynamics.
3. Add strict canonical JSON schema + cryptographic signature verification for certificates.
4. Add multi-agent aggregation experiment for Sybil/Byzantine robustness.
