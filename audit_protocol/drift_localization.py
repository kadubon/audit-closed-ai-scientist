"""Drift-mode and subgraph-local fault localization primitives."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Dict, Iterable, List, Sequence

import numpy as np


@dataclass(frozen=True)
class DriftLocalizationDecision:
    drift_triggered: bool
    alpha_drift: float
    global_e_value: float
    local_e_values: List[float]
    rejected_subgraphs: List[int]
    exempted_subgraphs: List[int]
    method: str


def drift_triggered(global_e_value: float, alpha_drift: float) -> bool:
    if not (0.0 < alpha_drift < 1.0):
        raise ValueError("alpha_drift must be in (0, 1)")
    return float(global_e_value) >= (1.0 / float(alpha_drift))


def _intersection_rejected_bonferroni_evalue(
    subset_indices: Sequence[int],
    local_e_values: Sequence[float],
    alpha_drift: float,
) -> bool:
    """Dependence-free intersection rejection rule via e-value Bonferroni bound.

    For subset S under intersection null:
    P(max_{k in S} e_k >= |S| / alpha) <= alpha.
    """
    subset_size = len(subset_indices)
    threshold = subset_size / alpha_drift
    return float(np.max([local_e_values[idx] for idx in subset_indices])) >= threshold


def closed_testing_localization(
    local_e_values: Sequence[float],
    alpha_drift: float = 0.05,
    max_subgraphs_for_exact: int = 10,
) -> Dict[str, object]:
    """Closed-testing style localization over subgraph no-drift nulls.

    Each elementary hypothesis H_k is "no drift in subgraph k".
    We reject H_k only if all intersection hypotheses containing k are rejected.
    """
    e_values = [float(v) for v in local_e_values]
    if len(e_values) == 0:
        raise ValueError("local_e_values must be non-empty")
    if not (0.0 < alpha_drift < 1.0):
        raise ValueError("alpha_drift must be in (0, 1)")

    k = len(e_values)
    if k > max_subgraphs_for_exact:
        # Fallback: dependence-free local alpha split.
        local_threshold = k / alpha_drift
        rejected = [idx for idx, value in enumerate(e_values) if value >= local_threshold]
        exempted = [idx for idx in range(k) if idx not in rejected]
        return {
            "method": "bonferroni_fallback",
            "rejected_subgraphs": rejected,
            "exempted_subgraphs": exempted,
            "local_threshold": local_threshold,
        }

    subset_rejections: Dict[tuple[int, ...], bool] = {}
    for subset_size in range(1, k + 1):
        for subset in combinations(range(k), subset_size):
            subset_rejections[subset] = _intersection_rejected_bonferroni_evalue(
                subset_indices=subset,
                local_e_values=e_values,
                alpha_drift=alpha_drift,
            )

    rejected = []
    for idx in range(k):
        supersets = [subset for subset in subset_rejections if idx in subset]
        if all(subset_rejections[subset] for subset in supersets):
            rejected.append(idx)
    exempted = [idx for idx in range(k) if idx not in rejected]
    return {
        "method": "closed_testing",
        "rejected_subgraphs": rejected,
        "exempted_subgraphs": exempted,
        "subset_rejections": {"-".join(str(i) for i in key): val for key, val in subset_rejections.items()},
    }


def localize_drift_mode(
    global_e_value: float,
    local_e_values: Iterable[float],
    alpha_drift: float = 0.05,
) -> DriftLocalizationDecision:
    """Produce drift-mode localization decision from global and local e-values."""
    local_vals = [float(v) for v in local_e_values]
    trigger = drift_triggered(global_e_value=global_e_value, alpha_drift=alpha_drift)
    if not trigger:
        return DriftLocalizationDecision(
            drift_triggered=False,
            alpha_drift=alpha_drift,
            global_e_value=float(global_e_value),
            local_e_values=local_vals,
            rejected_subgraphs=[],
            exempted_subgraphs=list(range(len(local_vals))),
            method="not_triggered",
        )

    localized = closed_testing_localization(local_vals, alpha_drift=alpha_drift)
    return DriftLocalizationDecision(
        drift_triggered=True,
        alpha_drift=alpha_drift,
        global_e_value=float(global_e_value),
        local_e_values=local_vals,
        rejected_subgraphs=list(localized["rejected_subgraphs"]),
        exempted_subgraphs=list(localized["exempted_subgraphs"]),
        method=str(localized["method"]),
    )
