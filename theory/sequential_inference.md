# Sequential Inference Notes

This repository uses always-valid e-values instead of fixed-horizon p-value procedures.

## Core bounded-increment setup

For score improvement increment `Delta_i` with known bounded range `[a, b]` and null margin `tau`:

```text
X_i = (Delta_i - tau) / (b - a),  so X_i in [-1, 1]
```

Under the null, `E[X_i | F_{i-1}] <= 0`.

## Grid-mixture e-process

For fixed grid `Lambda = {lambda_1, ..., lambda_m}` with `lambda_j in (0,1)`:

```text
E_n^(lambda_j) = Π_{i=1}^n (1 + lambda_j * X_i)
E_n = Σ_j pi_j E_n^(lambda_j)
```

with fixed mixture weights `pi_j >= 0`, `Σ_j pi_j = 1`.

Because each component and fixed nonnegative mixture remains a supermartingale under the null:

```text
P_0(sup_n E_n >= 1/alpha) <= alpha
```

This gives optional-stopping-safe error control.

## Batch candidate control

When `m` candidates are tried in one committed batch, this benchmark uses:

```text
accept candidate j only if e_j >= m / alpha_t
```

which gives dependence-free familywise control for that batch.

## Alpha-spending across epochs

For stream operation across epochs, alpha is budgeted via a geometric schedule:

```text
alpha_t = alpha_total * (1 - decay) * decay^t
```

with total spent alpha bounded by `alpha_total`.

## Practical interpretation in this repository

- Naive p-value workflows inflate discoveries under peeking, optional stopping, and candidate shopping.
- E-process workflows remain valid under continuous monitoring and precommitted logging constraints.
- Audit closure prevents hidden evidence pathways that would otherwise invalidate inference.
