# Integration Guide for AI Scientist Systems

This repository is designed to be embedded inside autonomous discovery stacks as a governance benchmark layer.
It is relevant to:
- autonomous research agents
- automated scientific discovery systems
- self-driving laboratory controllers
- agentic AI research pipelines

## Integration goals

Use this benchmark to answer:
- Does your agent inflate discoveries under adaptive search?
- Does your sequential testing remain valid under optional stopping?
- Can your update decisions be replayed from a public log?
- Does your pipeline fail closed under adversarial submissions?

## API entry points

- `benchmarks.run_benchmark(...)`
  - Returns comparative benchmark metrics for baseline vs audit-closed operation.

- `benchmarks.run_simulation_bundle(...)`
  - Runs all core simulations with a quick/standard profile.

- `benchmarks.benchmark.evaluate(my_ai_scientist)`
  - Evaluates an external AI scientist adapter under the benchmark data protocol.
  - Returns null-world false discovery rate and signal-world replication probability with Wilson intervals.

- `audit_protocol.AuditClosedScientist`
  - Wrap your candidate set and evidence streams in an audit-closed update loop.

- `audit_protocol.evaluate_hierarchical_sentinels`
  - Evaluate physical calibration branch decisions with primary/secondary sentinel checks.

- `audit_protocol.localize_drift_mode`
  - Perform subgraph-local drift localization after a global drift trigger.

- `audit_protocol.validate_certificate_or_raise`
  - Enforce minimal incorporation-certificate schema validity.

## Minimal adapter pattern

1. Convert your agent proposals into deterministic `CandidateModel`-like objects.
2. Commit candidate IDs before evaluating outcomes (`candidate_commitment` event).
3. For each candidate, compute bounded evidence increments and e-values.
4. Append evaluation events to `TransparencyLog`.
5. Compute final decision via `acceptance_from_public_log`.

Minimal sketch:

```python
from audit_protocol import AuditClosedScientist, AuditClosedConfig
from benchmarks import benchmark
from baseline_ai_scientist.hypothesis_generator import generate_hypotheses

scientist = AuditClosedScientist(AuditClosedConfig(total_alpha=0.05, alpha_decay=0.5), seed=42)
candidates = generate_hypotheses(n_candidates=20, seed=43, include_defaults=True)
decision = scientist.evaluate_epoch(epoch=0, candidates=candidates, x=x_array, y=y_array)
replay = scientist.replay_epoch(epoch=0)
assert replay["replay_matches"] and replay["log_integrity_ok"]

# External benchmark API
report = benchmark.evaluate(my_ai_scientist)
print(report["null_world"]["false_discovery_rate"])
print(report["signal_world"]["replication_probability"])
```

External adapter minimum contract:
- input: `candidates`, `x`, `y`, `alpha`, `seed`, `signal`
- output: `{"accepted": bool, "winner": str | None}`

## Extension points

- Replace synthetic generator with lab simulator or real lab stream.
- Replace candidate family with your symbolic regression/program synthesis outputs.
- Replace increment definition with your domain score under bounded contracts.
- Add domain integrity gates as additional logged predicates.

## Guardrails for safe integration

- Keep candidate generation and candidate evaluation role-separated.
- Ensure all pseudo-random sources are seeded and logged.
- Preserve append-only log semantics and verify checkpoints during replay.
- Fail closed if required commitment/evaluation entries are missing.
