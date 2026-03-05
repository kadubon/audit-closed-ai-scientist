# Security Audit Notes

This document summarizes the security posture of the benchmark implementation and residual risks.

## Threats modeled

1. Candidate spam and fabricated submissions.
2. Hidden candidate shopping outside declared candidate sets.
3. Replay nondeterminism and non-reproducible acceptance.
4. Log payload tampering after experiment execution.
5. Malformed incorporation certificates.
6. Randomness manipulation via hidden seed changes.

## Implemented controls

- Append-only hash-chained transparency log (`audit_protocol/transparency_log.py`).
- Merkle-root checkpoints for batch integrity verification.
- Optional HMAC checkpoint signing hook for witness anchoring.
- Fail-closed acceptance rule:
  - exactly one candidate commitment per epoch
  - unique candidate IDs
  - no uncommitted evaluations
  - no duplicate evaluations
  - no missing evaluations when strict mode is enabled
- Deterministic replay check in `AuditClosedScientist.replay_epoch`.
- Adversarial simulation includes explicit tamper-detection evaluation.
- Unit tests enforce fail-closed behavior under log/transcript tampering (`tests/test_security_audit_protocol.py`).
- Test cases include payload rewrite, `prev_hash` rewrite, commitment rewrite, `alpha_epoch` rewrite, and transcript entry deletion.
- Certificate schema validator rejects malformed protocol records (`audit_protocol/certificate_schema.py`).
- Fixed seed registries and config-hash recording reduce hidden randomness manipulation (`run_all_experiments.py`).

## Reproducibility attack surface

- If an attacker can rewrite both log entries and all checkpoint artifacts, local integrity checks alone are insufficient.
- Mitigation strategy:
  - publish checkpoints to independent witness channels (transparency servers, object storage, signed releases).
  - optionally use external signatures per checkpoint.

## Dependency risk

- Repository keeps a minimal dependency surface:
  - NumPy
  - SciPy
  - Matplotlib
- Versions are pinned in `requirements.txt` and `environment.yml`.

## Operational recommendations

1. Anchor every run checkpoint to an immutable external store.
2. Use detached signatures from at least one independent witness service.
3. Enforce immutable run manifests in CI before accepting benchmark updates.
4. Treat missing or malformed log entries as immediate protocol failure.

## Execute security checks

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Additional extension-module checks:
- `tests/test_protocol_extensions.py`
