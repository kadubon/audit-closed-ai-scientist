"""Hypothesis generation utilities for baseline AI scientist agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List

import numpy as np


FeatureMap = Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class CandidateModel:
    """A lightweight candidate model represented by a deterministic feature map."""

    name: str
    feature_map: FeatureMap
    description: str

    def transform(self, x: np.ndarray) -> np.ndarray:
        features = self.feature_map(x)
        if features.ndim == 1:
            features = features.reshape(-1, 1)
        return features


def _column(values: np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=float).reshape(-1, 1)


def default_hypotheses() -> List[CandidateModel]:
    """Canonical model library containing simple symbolic hypotheses."""
    return [
        CandidateModel(
            name="constant",
            feature_map=lambda x: np.zeros_like(x),
            description="y = c",
        ),
        CandidateModel(
            name="linear",
            feature_map=lambda x: _column(x),
            description="y = a + b*x",
        ),
        CandidateModel(
            name="quadratic",
            feature_map=lambda x: np.column_stack([x, x**2]),
            description="y = a + b*x + c*x^2",
        ),
        CandidateModel(
            name="cubic",
            feature_map=lambda x: np.column_stack([x, x**2, x**3]),
            description="y = a + b*x + c*x^2 + d*x^3",
        ),
        CandidateModel(
            name="sin_1x",
            feature_map=lambda x: _column(np.sin(x)),
            description="y = a + b*sin(x)",
        ),
        CandidateModel(
            name="sin_cos_1x",
            feature_map=lambda x: np.column_stack([np.sin(x), np.cos(x)]),
            description="y = a + b*sin(x) + c*cos(x)",
        ),
        CandidateModel(
            name="sin_2x",
            feature_map=lambda x: _column(np.sin(2.0 * x)),
            description="y = a + b*sin(2x)",
        ),
        CandidateModel(
            name="exp_decay",
            feature_map=lambda x: _column(np.exp(-np.abs(x))),
            description="y = a + b*exp(-|x|)",
        ),
    ]


def random_hypotheses(n_random: int, rng: np.random.Generator) -> List[CandidateModel]:
    """Randomized model proposals used to emulate candidate shopping."""
    hypotheses: List[CandidateModel] = []
    for idx in range(n_random):
        family = idx % 4
        if family == 0:
            omega = float(rng.uniform(0.3, 4.5))
            phase = float(rng.uniform(-np.pi, np.pi))
            hypotheses.append(
                CandidateModel(
                    name=f"rand_sin_{idx}",
                    feature_map=lambda x, w=omega, p=phase: _column(np.sin(w * x + p)),
                    description=f"y = a + b*sin({omega:.3f}x + {phase:.3f})",
                )
            )
        elif family == 1:
            omega = float(rng.uniform(0.3, 4.5))
            phase = float(rng.uniform(-np.pi, np.pi))
            hypotheses.append(
                CandidateModel(
                    name=f"rand_cos_{idx}",
                    feature_map=lambda x, w=omega, p=phase: _column(np.cos(w * x + p)),
                    description=f"y = a + b*cos({omega:.3f}x + {phase:.3f})",
                )
            )
        elif family == 2:
            degree = int(rng.integers(2, 6))
            hypotheses.append(
                CandidateModel(
                    name=f"rand_poly_{idx}",
                    feature_map=lambda x, d=degree: np.column_stack(
                        [x**p for p in range(1, d + 1)]
                    ),
                    description=f"y = a + polynomial_degree_{degree}(x)",
                )
            )
        else:
            center = float(rng.uniform(-2.5, 2.5))
            width = float(rng.uniform(0.3, 1.5))
            hypotheses.append(
                CandidateModel(
                    name=f"rand_rbf_{idx}",
                    feature_map=lambda x, c=center, w=width: _column(
                        np.exp(-0.5 * ((x - c) / w) ** 2)
                    ),
                    description=f"y = a + b*exp(-(x-{center:.3f})^2/(2*{width:.3f}^2))",
                )
            )
    return hypotheses


def generate_hypotheses(
    n_candidates: int,
    seed: int | None = None,
    include_defaults: bool = True,
) -> List[CandidateModel]:
    """Generate candidate models for an epoch."""
    if n_candidates <= 0:
        return []

    rng = np.random.default_rng(seed)
    pool: List[CandidateModel] = []
    if include_defaults:
        pool.extend(default_hypotheses())
    if len(pool) < n_candidates:
        pool.extend(random_hypotheses(n_candidates - len(pool), rng))
    return pool[:n_candidates]


def find_candidate_by_name(
    candidates: Iterable[CandidateModel], candidate_name: str
) -> CandidateModel | None:
    for candidate in candidates:
        if candidate.name == candidate_name:
            return candidate
    return None
