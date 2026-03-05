"""Sequential test wrappers around e-processes and alpha-spending."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from audit_protocol.e_process import DEFAULT_LAMBDAS, GridMixtureEProcess


@dataclass
class SequentialTestResult:
    crossed_threshold: bool
    stopping_time: int
    final_e_value: float
    threshold: float
    trajectory: np.ndarray


class AlphaSpendingSchedule:
    """Geometric alpha-spending schedule with total spend bounded by total_alpha."""

    def __init__(self, total_alpha: float = 0.05, decay: float = 0.5) -> None:
        if not (0.0 < total_alpha < 1.0):
            raise ValueError("total_alpha must be in (0, 1)")
        if not (0.0 < decay < 1.0):
            raise ValueError("decay must be in (0, 1)")
        self.total_alpha = float(total_alpha)
        self.decay = float(decay)

    def alpha_for_epoch(self, epoch: int) -> float:
        if epoch < 0:
            raise ValueError("epoch must be nonnegative")
        return self.total_alpha * (1.0 - self.decay) * (self.decay**epoch)

    def spent_through_epoch(self, epoch: int) -> float:
        if epoch < 0:
            return 0.0
        return self.total_alpha * (1.0 - self.decay ** (epoch + 1))


def evalue_batch_threshold(alpha_epoch: float, n_candidates: int) -> float:
    if alpha_epoch <= 0.0:
        raise ValueError("alpha_epoch must be positive")
    if n_candidates <= 0:
        raise ValueError("n_candidates must be positive")
    return float(n_candidates / alpha_epoch)


def run_grid_e_test(
    increments: np.ndarray,
    alpha_epoch: float,
    n_candidates: int,
    lambdas: Sequence[float] = DEFAULT_LAMBDAS,
    stop_on_threshold: bool = True,
) -> SequentialTestResult:
    process = GridMixtureEProcess(lambdas=lambdas)
    threshold = evalue_batch_threshold(alpha_epoch=alpha_epoch, n_candidates=n_candidates)
    crossed = False
    stopping_time = len(increments)
    trajectory = []

    for idx, increment in enumerate(increments, start=1):
        value = process.update(float(increment))
        trajectory.append(value)
        if stop_on_threshold and value >= threshold:
            crossed = True
            stopping_time = idx
            break

    if not trajectory:
        trajectory = [process.value]
        stopping_time = 0
    final_e = float(trajectory[-1])
    if not stop_on_threshold and final_e >= threshold:
        crossed = True

    return SequentialTestResult(
        crossed_threshold=crossed,
        stopping_time=int(stopping_time),
        final_e_value=final_e,
        threshold=threshold,
        trajectory=np.asarray(trajectory, dtype=float),
    )
