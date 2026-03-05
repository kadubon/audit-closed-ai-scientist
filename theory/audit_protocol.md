# Audit-Closed Protocol (Operational View)

This repository implements the core governance principle from the paper:

```text
Accept_t = f(Log_0:t)
```

where:
- `Log_0:t` is the public append-only transparency log prefix up to epoch `t`.
- `f` is a deterministic acceptance function.

## Why this matters

Naive autonomous discovery agents can make decisions from hidden state:
- unpublished failed hypotheses
- private peeking traces
- unlogged data transforms
- non-replayable randomness

Audit-closed governance removes this hidden degree of freedom by requiring that all acceptance decisions are replayable from public artifacts.

## Protocol elements in this repository

1. `audit_protocol/transparency_log.py`
- Hash-chained append-only log.
- Merkle-root checkpoints for root-level integrity verification.
- Optional HMAC checkpoint signatures for external witness anchoring.
- Verifiable integrity of event order and payloads.

2. `audit_protocol/audit_closed_update.py`
- Candidate commitment before evaluation.
- Per-candidate e-value transcript logging.
- Fail-closed checks (duplicate/missing/uncommitted candidate evaluations).
- Deterministic acceptance from log state only.
- Deterministic replay check (`replay_epoch`).

3. `audit_protocol/sequential_tests.py`
- Geometric alpha-spending across epochs.
- Dependence-free thresholding rule `e >= m / alpha_t` for batch candidate sets.

4. `audit_protocol/e_process.py`
- Grid-mixture e-process for bounded sequential increments.
- Optional variance-adaptive variant for contextual/importance-weighted increments.

## Minimal event flow per epoch

1. `candidate_commitment`
- Log candidate IDs before outcomes are consumed.

2. `candidate_evaluation`
- Log deterministic evidence transcript summaries (`final_e_value`, stopping time, bounded increment statistics).

3. `epoch_decision`
- Log output of deterministic acceptance rule.

## Security and governance interpretation

This does not claim truth; it claims procedural validity:
- no hidden candidate shopping
- no hidden stopping rule
- reproducible and externally checkable decision path
- bounded Type-I risk under sequential monitoring through e-values
