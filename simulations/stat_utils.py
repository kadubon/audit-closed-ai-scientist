"""Statistical utility functions used across simulations."""

from __future__ import annotations

from math import sqrt
from typing import Dict

from scipy.stats import norm


def wilson_interval(successes: int, trials: int, confidence: float = 0.95) -> Dict[str, float]:
    """Wilson score interval for binomial proportions."""
    if trials <= 0:
        return {"rate": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": float(trials)}
    if successes < 0 or successes > trials:
        raise ValueError("successes must satisfy 0 <= successes <= trials")
    if not (0.0 < confidence < 1.0):
        raise ValueError("confidence must be in (0, 1)")

    z = float(norm.ppf(0.5 + confidence / 2.0))
    p = successes / trials
    denom = 1.0 + z**2 / trials
    center = (p + z**2 / (2.0 * trials)) / denom
    radius = (
        z
        * sqrt((p * (1.0 - p) / trials) + (z**2 / (4.0 * trials**2)))
        / denom
    )
    low = max(0.0, center - radius)
    high = min(1.0, center + radius)
    return {"rate": float(p), "ci_low": float(low), "ci_high": float(high), "n": float(trials)}
