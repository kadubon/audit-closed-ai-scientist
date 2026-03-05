"""Experiment execution helpers for synthetic AI scientist benchmarks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
from scipy import stats

from baseline_ai_scientist.hypothesis_generator import CandidateModel


@dataclass
class ExperimentData:
    x: np.ndarray
    y: np.ndarray


def hidden_law(x: np.ndarray, signal_strength: float = 1.0) -> np.ndarray:
    return signal_strength * np.sin(x)


def generate_synthetic_data(
    n_samples: int,
    noise_std: float = 0.35,
    seed: int | None = None,
    signal: bool = True,
    signal_strength: float = 1.0,
    x_range: Tuple[float, float] = (-np.pi, np.pi),
) -> ExperimentData:
    rng = np.random.default_rng(seed)
    x = rng.uniform(x_range[0], x_range[1], size=n_samples)
    clean = hidden_law(x, signal_strength=signal_strength) if signal else np.zeros_like(x)
    y = clean + rng.normal(0.0, noise_std, size=n_samples)
    return ExperimentData(x=x, y=y)


def split_train_test(
    x: np.ndarray,
    y: np.ndarray,
    train_fraction: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n = len(x)
    split = int(np.clip(round(n * train_fraction), 1, n - 1))
    return x[:split], y[:split], x[split:], y[split:]


def _fit_linear_model(features: np.ndarray, y: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(features)), features])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return coef


def _predict_linear_model(features: np.ndarray, coef: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(features)), features])
    return design @ coef


def one_sided_mean_positive_pvalue(samples: np.ndarray) -> Tuple[float, float]:
    """One-sided test for H0: mean <= 0 vs H1: mean > 0."""
    values = np.asarray(samples, dtype=float)
    n = len(values)
    if n < 2:
        return 1.0, 0.0

    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    if std <= 1e-12:
        if mean > 0.0:
            return 0.0, np.inf
        if mean < 0.0:
            return 1.0, -np.inf
        return 1.0, 0.0

    t_stat = mean / (std / np.sqrt(n))
    p_value = float(stats.t.sf(t_stat, df=n - 1))
    return p_value, t_stat


def evaluate_candidate(
    candidate: CandidateModel,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
) -> Dict[str, float]:
    """Fit candidate on train split and evaluate predictive gain on test split."""
    baseline = float(np.mean(y_train))
    baseline_pred = np.full_like(y_test, fill_value=baseline, dtype=float)
    baseline_loss = (y_test - baseline_pred) ** 2

    train_features = candidate.transform(x_train)
    test_features = candidate.transform(x_test)
    coef = _fit_linear_model(train_features, y_train)
    candidate_pred = _predict_linear_model(test_features, coef)
    candidate_loss = (y_test - candidate_pred) ** 2

    improvement = baseline_loss - candidate_loss
    p_value, t_stat = one_sided_mean_positive_pvalue(improvement)

    return {
        "p_value": float(p_value),
        "t_stat": float(t_stat),
        "mean_improvement": float(np.mean(improvement)),
        "std_improvement": float(np.std(improvement, ddof=1)) if len(improvement) > 1 else 0.0,
        "mse_baseline": float(np.mean(baseline_loss)),
        "mse_candidate": float(np.mean(candidate_loss)),
    }


def prepare_candidate_increment_stream(
    candidate: CandidateModel,
    x: np.ndarray,
    y: np.ndarray,
    train_fraction: float = 0.4,
    clip_bound: float = 2.0,
) -> Dict[str, np.ndarray | float]:
    """Prepare bounded increments for e-process testing."""
    x_train, y_train, x_test, y_test = split_train_test(x, y, train_fraction=train_fraction)
    baseline = float(np.mean(y_train))
    baseline_pred = np.full_like(y_test, fill_value=baseline, dtype=float)
    baseline_loss = (y_test - baseline_pred) ** 2

    coef = _fit_linear_model(candidate.transform(x_train), y_train)
    candidate_pred = _predict_linear_model(candidate.transform(x_test), coef)
    candidate_loss = (y_test - candidate_pred) ** 2
    improvement = baseline_loss - candidate_loss
    increments = np.clip(improvement / clip_bound, -1.0, 1.0)

    return {
        "increments": increments,
        "mean_improvement": float(np.mean(improvement)),
        "mean_increment": float(np.mean(increments)),
        "n_increments": float(len(increments)),
    }
