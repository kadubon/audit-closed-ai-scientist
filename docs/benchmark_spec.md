# Benchmark Specification

This document defines what the benchmark measures and how to interpret outputs.

## Objective

Evaluate whether an AI scientist pipeline remains statistically reliable and audit-replayable under adaptive experimentation.

## Compared systems

1. Baseline naive pipeline:
- adaptive search with naive significance-based selection

2. Audit-closed pipeline:
- committed candidate set
- logged sequential evidence
- fail-closed replay checks
- e-value acceptance with alpha accounting

## Core metrics

1. False discovery rate (FDR):
- proportion of null-world trials that are falsely accepted.

2. Replication success:
- proportion of accepted positive-signal claims that replicate on fresh data.

3. Sequential evidence stability:
- deviation from nominal false-positive control under optional stopping.

4. Adversarial robustness:
- false acceptance under malicious submission pressure and tampering tests.

5. Sentinel hierarchy safety:
- false sensor recalibration vs freeze tradeoff under sentinel ambiguity.

6. Drift localization availability:
- unaffected subgraph uptime under global freeze vs localized exemptions.

7. Certificate integrity enforcement:
- schema-level tamper detection and false reject behavior.

## Statistical reporting

- Monte Carlo estimates include Wilson confidence intervals where applicable.
- Standard profile is intended for research reporting.
- Quick profile is intended for rapid smoke checks.

## Output contract

Primary artifact:
- `results/experiment_results.json`

Expected top-level sections:
- `p_hacking_simulation`
- `candidate_shopping`
- `optional_stopping`
- `power_curve`
- `adversarial_agents`
- `sentinel_hierarchy`
- `drift_localization`
- `certificate_schema_validation`
- `benchmark`
- `generated_figures`
- `reproducibility`

## External evaluation API

The benchmark exposes an external adapter API:
- `benchmarks.benchmark.evaluate(my_ai_scientist)`

Expected external decision contract:
- `accepted` (required)
- `winner` or `best_candidate_name` (recommended for replication accounting)

This API enables direct integration with autonomous research agents and AI scientist frameworks.
