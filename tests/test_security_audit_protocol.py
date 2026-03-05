"""Security-focused tests for audit protocol integrity checks."""

from __future__ import annotations

import copy
import unittest

from audit_protocol.audit_closed_update import AuditClosedConfig, AuditClosedScientist, acceptance_from_public_log
from audit_protocol.transparency_log import TransparencyLog
from baseline_ai_scientist.experiment_runner import generate_synthetic_data
from baseline_ai_scientist.hypothesis_generator import generate_hypotheses


class AuditProtocolSecurityTests(unittest.TestCase):
    def _build_logged_epoch(self) -> AuditClosedScientist:
        config = AuditClosedConfig(total_alpha=0.1, alpha_decay=0.5)
        scientist = AuditClosedScientist(config=config, seed=11)
        data = generate_synthetic_data(n_samples=80, noise_std=0.35, seed=19, signal=True)
        candidates = generate_hypotheses(n_candidates=4, seed=23, include_defaults=True)
        scientist.evaluate_epoch(epoch=0, candidates=candidates, x=data.x, y=data.y)
        return scientist

    def test_acceptance_fails_when_payload_is_tampered(self) -> None:
        scientist = self._build_logged_epoch()
        tampered_entries = copy.deepcopy(scientist.log.entries)
        tampered_entries[2].payload["final_e_value"] = 9999.0
        with self.assertRaises(ValueError):
            acceptance_from_public_log(tampered_entries, epoch=0)

    def test_acceptance_fails_when_prev_hash_is_tampered(self) -> None:
        scientist = self._build_logged_epoch()
        tampered_entries = copy.deepcopy(scientist.log.entries)
        tampered_entries[1].prev_hash = "BAD_HASH"
        with self.assertRaises(ValueError):
            acceptance_from_public_log(tampered_entries, epoch=0)

    def test_serialized_payload_verification_detects_tampering(self) -> None:
        log = TransparencyLog()
        log.append("genesis", {"total_alpha": 0.1, "alpha_decay": 0.5})
        log.append("candidate_commitment", {"epoch": 0, "candidate_names": ["a"]})
        log.append(
            "candidate_evaluation",
            {"epoch": 0, "candidate_name": "a", "final_e_value": 0.2, "alpha_epoch": 0.05, "batch_threshold": 20.0},
        )
        payload = {"integrity_ok": log.verify_integrity(), "checkpoint": log.checkpoint(), "entries": log.to_serializable()}
        self.assertTrue(TransparencyLog.verify_serialized_payload(payload))

        tampered = copy.deepcopy(payload)
        tampered["entries"][2]["payload"]["final_e_value"] = -100.0
        self.assertFalse(TransparencyLog.verify_serialized_payload(tampered))

    def test_missing_candidate_evaluation_fails_closed(self) -> None:
        log = TransparencyLog()
        log.append(
            "genesis",
            {
                "total_alpha": 0.1,
                "alpha_decay": 0.5,
                "lambdas": [0.1, 0.3],
                "train_fraction": 0.4,
                "clip_bound": 2.0,
            },
        )
        log.append("candidate_commitment", {"epoch": 0, "candidate_names": ["a", "b"]})
        log.append(
            "candidate_evaluation",
            {"epoch": 0, "candidate_name": "a", "final_e_value": 0.5, "alpha_epoch": 0.05, "batch_threshold": 40.0},
        )
        with self.assertRaises(ValueError):
            acceptance_from_public_log(log.entries, epoch=0)

    def test_acceptance_fails_when_alpha_epoch_is_tampered(self) -> None:
        scientist = self._build_logged_epoch()
        tampered_entries = copy.deepcopy(scientist.log.entries)
        for entry in tampered_entries:
            if entry.event_type == "candidate_evaluation":
                entry.payload["alpha_epoch"] = 0.123456
                break
        with self.assertRaises(ValueError):
            acceptance_from_public_log(tampered_entries, epoch=0)

    def test_serialized_payload_verification_fails_on_entry_deletion(self) -> None:
        scientist = self._build_logged_epoch()
        payload = {
            "integrity_ok": scientist.log.verify_integrity(),
            "checkpoint": scientist.log.checkpoint(),
            "entries": scientist.log.to_serializable(),
        }
        self.assertTrue(TransparencyLog.verify_serialized_payload(payload))

        tampered = copy.deepcopy(payload)
        del tampered["entries"][1]
        self.assertFalse(TransparencyLog.verify_serialized_payload(tampered))

    def test_acceptance_fails_when_commitment_is_modified(self) -> None:
        scientist = self._build_logged_epoch()
        tampered_entries = copy.deepcopy(scientist.log.entries)
        for entry in tampered_entries:
            if entry.event_type == "candidate_commitment":
                entry.payload["candidate_names"] = entry.payload["candidate_names"][:-1]
                break
        with self.assertRaises(ValueError):
            acceptance_from_public_log(tampered_entries, epoch=0)


if __name__ == "__main__":
    unittest.main()
