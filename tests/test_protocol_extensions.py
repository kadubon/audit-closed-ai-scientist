"""Tests for newly added protocol extension modules."""

from __future__ import annotations

import unittest

from audit_protocol.certificate_schema import minimal_certificate_template, validate_certificate
from audit_protocol.drift_localization import localize_drift_mode
from audit_protocol.physical_sentinels import (
    SentinelObservation,
    SentinelThresholds,
    evaluate_hierarchical_sentinels,
)


class ProtocolExtensionTests(unittest.TestCase):
    def test_primary_failure_blocks_sensor_recalibration(self) -> None:
        obs = SentinelObservation(
            primary_health_score=0.95,
            secondary_health_score=0.2,
            sensor_residual_score=0.95,
            secondary_primary_gap=0.1,
            spoof_score=0.0,
        )
        decision = evaluate_hierarchical_sentinels(observation=obs, thresholds=SentinelThresholds())
        self.assertEqual(decision.branch, "sentinel_maintenance")
        self.assertFalse(decision.sensor_recalibration_allowed)

    def test_drift_localization_rejects_affected_subgraph(self) -> None:
        decision = localize_drift_mode(
            global_e_value=160.0,
            local_e_values=[160.0, 0.4, 0.6, 0.5],
            alpha_drift=0.05,
        )
        self.assertTrue(decision.drift_triggered)
        self.assertIn(0, decision.rejected_subgraphs)
        self.assertIn(1, decision.exempted_subgraphs)
        self.assertIn(2, decision.exempted_subgraphs)
        self.assertIn(3, decision.exempted_subgraphs)

    def test_certificate_template_validates(self) -> None:
        cert = minimal_certificate_template()
        errors = validate_certificate(cert)
        self.assertEqual(errors, [])

    def test_certificate_missing_key_is_rejected(self) -> None:
        cert = minimal_certificate_template()
        del cert["gates"]["progress"]["mode"]
        errors = validate_certificate(cert)
        self.assertTrue(any("certificate.gates.progress.mode" in err for err in errors))


if __name__ == "__main__":
    unittest.main()
