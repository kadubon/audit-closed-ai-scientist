# Result Summary

Latest run:

```bash
python run_all_experiments.py --profile standard
```

Source of truth: `results/experiment_results.json`

This summary is intentionally conservative and only reports what is directly supported by implemented experiments.

## Core statistical findings

## 1) Many-hypothesis inflation (null world)

- 5 hypotheses:
  - naive false discovery rate: `0.193`
  - Bonferroni: `0.0267`
- 1000 hypotheses:
  - naive false discovery rate: `1.000`
  - Bonferroni: `0.050`

Interpretation:
- naive min-p publication is highly vulnerable to search-volume inflation.

## 2) Candidate shopping (null world)

Null false-positive rates by number of candidate designs:

- 5 designs: naive `0.134`, e-process `0.000`
- 10 designs: naive `0.237`, e-process `0.000`
- 25 designs: naive `0.511`, e-process `0.000`
- 50 designs: naive `0.717`, e-process `0.000`

Interpretation:
- repeated design shopping can dominate apparent discoveries in naive pipelines.

## 3) Optional stopping calibration (400 looks, null world)

- peeking p-value false-positive rate: `0.339`
- fixed-horizon p-value false-positive rate: `0.0425`
- sequential e-value false-positive rate: `0.0367`

Interpretation:
- p-values are calibrated at fixed horizon but not under continuous peeking.
- sequential e-values remain close to nominal control in this benchmark.

Calibration-deviation summary across look grid (from integrated benchmark):
- mean absolute alpha deviation for peeking p-values: `0.2084`
- mean absolute alpha deviation for sequential e-values: `0.0374`

Interpretation:
- across the tested sequential horizons, e-values stay substantially closer to nominal alpha than peeking p-values.

## 4) Power curve (effect-size sweep)

At effect size `0.0`:
- peeking p detection: `0.334`
- fixed-horizon p detection: `0.0363`
- e-value detection: `0.020`

At effect size `0.4`:
- peeking p detection: `1.000`
- fixed-horizon p detection: `1.000`
- e-value detection: `1.000`

Interpretation:
- e-values are conservative near null and retain strong power at larger effects.

## Integrated benchmark findings

## 5) Budget-matched baseline vs audit-closed

False discovery rate under global null:
- baseline: `0.653` (95% CI: `0.599` to `0.703`)
- audit-closed: `0.000` (95% CI upper bound: `0.0119`)

Replication success among accepted positive-signal discoveries:
- baseline: `0.722`
- audit-closed: `0.809`

## 6) Adversarial pressure (100 malicious candidates)

- baseline false acceptance: `1.000`
- audit-closed false acceptance: `0.002`
- replay match rate: `1.000`
- tamper detection rate: `1.000`

Interpretation:
- audit-closed controls substantially improve robustness in this adversarial model.

## Newly implemented protocol-extension findings

## 7) Physical sentinel hierarchy stress

- single sentinel false sensor recalibration rate: `0.145`
- hierarchical sentinel false sensor recalibration rate: `0.000`
- spoof detection rate: `1.000` in both approaches
- operational freeze rate:
  - single sentinel: `0.0436`
  - hierarchical sentinel: `0.288`

Interpretation:
- hierarchical sentinels reduce miscalibration risk but increase freeze/maintenance decisions in this simulation.

## 8) Drift localization stress

- unaffected-subgraph uptime:
  - global freeze: `0.000`
  - localized exemption: `1.000`
- false local quarantine rate: `0.000`
- affected-subgraph detection rate: `0.863`

Interpretation:
- local exemptions preserve unaffected components while retaining high affected-branch detection in this setting.

## 9) Certificate schema validation stress

- false reject rate on valid minimal certificates: `0.000`
- tamper detection rate on invalid/mutated certificates: `1.000`

Interpretation:
- the minimal schema validator is effective for structural tampering in this benchmark.

## Scientific scope and limits

Implemented and evaluated:
- sequential validity under optional stopping
- multiplicity/candidate-shopping controls
- deterministic audit-closed replay logic
- hierarchical sentinel branch logic (benchmark abstraction)
- subgraph-local drift localization (benchmark abstraction)
- minimal incorporation-certificate schema validation

Not fully implemented yet:
- full physical attestation and hardware trust-chain operations
- full root-memory erosion dynamics (`m_ext`, `kappa_t`) in a complete transition controller
- complete appendix-level certificate cryptographic verification stack

## Reproduce

```bash
python -m pip install -r requirements.txt
python run_all_experiments.py --profile standard
python regenerate_figures.py
python -m unittest discover -s tests -p "test_*.py"
```
