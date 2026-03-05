# Configuration Files

- `quick.json`: low-cost exploratory run profile.
- `standard.json`: reporting-oriented run profile.

Schema highlights:
- `alpha`: nominal significance/evidence level.
- `seeds`: fixed RNG seeds per simulation block.
- `sample_sizes`: Monte Carlo run counts.
- `grids`: hypothesis/design/look/effect-size grids.
- `settings`: simulation-specific scalar settings.

Current profiles also include:
- sentinel hierarchy stress-test settings
- drift localization settings (`drift_subgraphs`, `drift_alpha`)
- certificate schema validation sample sizes
