"""Tests for external benchmark integration API."""

from __future__ import annotations

import unittest

from benchmarks.api import DiscoveryValidityHarness, ExternalEvaluationConfig
from baseline_ai_scientist.experiment_runner import evaluate_candidate, split_train_test


class _AlwaysRejectScientist:
    def evaluate_trial(self, **kwargs):
        return {"accepted": False, "winner": None}


def _malformed_scientist(**kwargs):
    return {"winner": "sin_1x"}


def _simple_naive_scientist(**kwargs):
    candidates = kwargs["candidates"]
    x = kwargs["x"]
    y = kwargs["y"]
    alpha = kwargs["alpha"]

    x_train, y_train, x_test, y_test = split_train_test(x, y, train_fraction=0.5)
    best = None
    best_p = 1.0
    for candidate in candidates:
        pval = evaluate_candidate(candidate, x_train, y_train, x_test, y_test)["p_value"]
        if pval < best_p:
            best_p = float(pval)
            best = candidate.name
    return {"accepted": bool(best_p < alpha), "winner": best}


class BenchmarkApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = DiscoveryValidityHarness(
            ExternalEvaluationConfig(
                n_runs=20,
                n_candidates=20,
                n_samples=120,
                seed=501,
            )
        )

    def test_evaluate_accepts_external_callable(self) -> None:
        result = self.harness.evaluate(_simple_naive_scientist)
        self.assertIn("null_world", result)
        self.assertIn("signal_world", result)
        self.assertIn("interface_diagnostics", result)

    def test_interface_errors_reported_for_malformed_agent(self) -> None:
        result = self.harness.evaluate(_malformed_scientist)
        self.assertGreaterEqual(result["interface_diagnostics"]["null_world_error_rate"], 0.9)
        self.assertGreaterEqual(result["interface_diagnostics"]["signal_world_error_rate"], 0.9)

    def test_always_reject_agent_has_zero_fdr(self) -> None:
        result = self.harness.evaluate(_AlwaysRejectScientist())
        self.assertEqual(result["null_world"]["false_discovery_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()

