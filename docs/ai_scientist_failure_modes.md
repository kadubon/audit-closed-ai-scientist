# AI Scientist Failure Modes

This document maps common autonomous-discovery failure modes to the simulations in this repository.

## 1) Optional stopping (continuous peeking)

Failure mode:
- Agent monitors significance after every new sample.
- Stops at first `p < alpha`.

Impact:
- Strong false-discovery inflation under the null.

Simulation:
- `simulations/optional_stopping.py`

Mitigation:
- Always-valid e-process with stopping rule `E_t >= 1/alpha`.

## 2) Candidate shopping

Failure mode:
- Agent tries many experiment designs/candidate pipelines and reports only the best result.

Impact:
- Hidden multiplicity and selection bias.

Simulation:
- `simulations/candidate_shopping.py`

Mitigation:
- Candidate-set commitment in public log.
- Batch e-value thresholding with candidate-count correction.
- Fail-closed rejection for duplicate/missing evaluation transcripts.

## 3) Many-hypothesis inflation / p-hacking

Failure mode:
- Agent generates huge hypothesis pools and reports the minimum p-value.

Impact:
- Discovery claims become mostly artifacts of search volume.

Simulation:
- `simulations/p_hacking_simulation.py`

Mitigation:
- Logged finite candidate set and e-process-based multiplicity control.

## 4) Adversarial experiment agents

Failure mode:
- Fabricated data submissions.
- Hypothesis spam to game selection.

Impact:
- Naive pipelines can accept fabricated discoveries.

Simulation:
- `simulations/adversarial_agents.py`

Mitigation:
- Integrity gate and rejection of unattested submissions.
- Audit-closed deterministic replay from public log.
- Checkpoint root verification detects post-hoc log tampering.

## 5) Non-replayable scientific governance

Failure mode:
- Final decision depends on hidden internal state, undocumented retries, or private checkpoints.

Impact:
- External verifiers cannot reproduce acceptance path.

Mitigation in this repository:
- `audit_protocol/transparency_log.py`
- `audit_protocol/audit_closed_update.py`
- deterministic acceptance rule:

```text
Accept_t = f(Log_0:t)
```

## 6) Sentinel ambiguity (sensor aging vs sentinel aging)

Failure mode:
- single-sentinel calibration cannot separate sensor-side drift from sentinel-side degradation.

Impact:
- wrong sensor recalibration can amplify measurement inconsistency.

Simulation:
- `simulations/sentinel_hierarchy.py`

Mitigation:
- hierarchical primary/secondary sentinel branch logic.
- primary-failure rule blocks sensor recalibration in that epoch.

## 7) Global drift freeze paralysis

Failure mode:
- global drift trigger quarantines all subgraphs, including unaffected parts.

Impact:
- avoidable availability loss and unnecessary downtime.

Simulation:
- `simulations/drift_localization_simulation.py`

Mitigation:
- local drift tests with closed-testing style localization.
- unaffected subgraphs can be exempted when local no-drift is not rejected.
