"""Always-valid e-process utilities for sequential testing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


DEFAULT_LAMBDAS = (0.1, 0.3, 0.5, 0.7, 0.9)


def _normalized_weights(size: int, weights: Sequence[float] | None = None) -> np.ndarray:
    if weights is None:
        return np.full(size, 1.0 / size, dtype=float)
    arr = np.asarray(weights, dtype=float)
    if arr.shape != (size,):
        raise ValueError("weights must have the same length as lambdas")
    if np.any(arr < 0):
        raise ValueError("weights must be nonnegative")
    s = float(np.sum(arr))
    if s <= 0:
        raise ValueError("weights must sum to a positive value")
    return arr / s


@dataclass
class EProcessSnapshot:
    time: int
    value: float


class GridMixtureEProcess:
    """Grid-mixture betting e-process for bounded increments in [-1, 1]."""

    def __init__(
        self,
        lambdas: Sequence[float] = DEFAULT_LAMBDAS,
        weights: Sequence[float] | None = None,
    ) -> None:
        self.lambdas = np.asarray(lambdas, dtype=float)
        if np.any(self.lambdas <= 0.0) or np.any(self.lambdas >= 1.0):
            raise ValueError("lambdas must be in (0, 1)")
        self.weights = _normalized_weights(len(self.lambdas), weights)
        self.components = np.ones(len(self.lambdas), dtype=float)
        self.snapshots: list[EProcessSnapshot] = []

    @property
    def value(self) -> float:
        return float(np.dot(self.weights, self.components))

    def update(self, increment: float) -> float:
        x = float(np.clip(increment, -1.0, 1.0))
        factors = 1.0 + self.lambdas * x
        factors = np.maximum(factors, 1e-12)
        self.components *= factors
        self.snapshots.append(EProcessSnapshot(time=len(self.snapshots) + 1, value=self.value))
        return self.value

    def run(self, increments: Iterable[float]) -> np.ndarray:
        values = []
        for inc in increments:
            values.append(self.update(float(inc)))
        return np.asarray(values, dtype=float)


class VarianceAdaptiveEProcess:
    """Predictable variance-adaptive e-process for weighted increments."""

    def __init__(
        self,
        base_lambdas: Sequence[float] = DEFAULT_LAMBDAS,
        weights: Sequence[float] | None = None,
        ema_decay: float = 0.95,
        init_variance: float = 1.0,
    ) -> None:
        self.base_lambdas = np.asarray(base_lambdas, dtype=float)
        if np.any(self.base_lambdas <= 0.0):
            raise ValueError("base lambdas must be positive")
        self.weights = _normalized_weights(len(self.base_lambdas), weights)
        self.components = np.ones(len(self.base_lambdas), dtype=float)
        self.ema_decay = float(np.clip(ema_decay, 0.0, 0.999))
        self.variance_proxy = float(max(init_variance, 1e-8))
        self.snapshots: list[EProcessSnapshot] = []

    @property
    def value(self) -> float:
        return float(np.dot(self.weights, self.components))

    def update(self, raw_increment: float, importance_weight: float = 1.0) -> float:
        y = float(raw_increment)
        w = max(1.0, abs(float(importance_weight)))
        scale = np.sqrt(max(self.variance_proxy, 1e-8))
        adaptive_lambdas = np.minimum(self.base_lambdas / scale, 1.0 / (2.0 * w))
        factors = 1.0 + adaptive_lambdas * y
        factors = np.maximum(factors, 1e-12)
        self.components *= factors
        self.variance_proxy = self.ema_decay * self.variance_proxy + (1.0 - self.ema_decay) * (y**2)
        self.snapshots.append(EProcessSnapshot(time=len(self.snapshots) + 1, value=self.value))
        return self.value
