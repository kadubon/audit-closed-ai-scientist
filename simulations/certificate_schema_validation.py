"""Stress test for minimal incorporation-certificate schema validation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Dict

import numpy as np

from audit_protocol.certificate_schema import minimal_certificate_template, validate_certificate
from simulations.stat_utils import wilson_interval


def _corrupt_certificate(cert: Dict[str, object], rng: np.random.Generator) -> Dict[str, object]:
    corrupted = copy.deepcopy(cert)
    mode = int(rng.integers(0, 5))
    if mode == 0:
        corrupted.pop("genesis", None)
    elif mode == 1:
        corrupted["gates"]["physical_coherence"]["branch"] = "invalid_branch"
    elif mode == 2:
        corrupted["gates"]["progress"]["mode"] = "invalid_mode"
    elif mode == 3:
        corrupted["gates"]["drift"]["external_cert_bit"] = "2"
    else:
        corrupted["data"]["D_A"].pop("digest", None)
    return corrupted


def run_simulation(
    n_valid: int = 200,
    n_invalid: int = 400,
    seed: int = 2034,
    output_path: str | None = None,
) -> Dict[str, object]:
    rng = np.random.default_rng(seed)

    valid_rejected = 0
    invalid_detected = 0

    for _ in range(n_valid):
        cert = minimal_certificate_template()
        cert["epoch"] = int(rng.integers(0, 10_000))
        errors = validate_certificate(cert)
        if len(errors) > 0:
            valid_rejected += 1

    for _ in range(n_invalid):
        cert = minimal_certificate_template()
        cert["epoch"] = int(rng.integers(0, 10_000))
        corrupted = _corrupt_certificate(cert, rng=rng)
        errors = validate_certificate(corrupted)
        if len(errors) > 0:
            invalid_detected += 1

    valid_ci = wilson_interval(valid_rejected, n_valid)
    invalid_ci = wilson_interval(invalid_detected, n_invalid)
    result: Dict[str, object] = {
        "simulation": "certificate_schema_validation",
        "n_valid": n_valid,
        "n_invalid": n_invalid,
        "confidence_level": 0.95,
        "false_reject_rate_valid_certificates": valid_ci["rate"],
        "false_reject_rate_valid_certificates_ci_low": valid_ci["ci_low"],
        "false_reject_rate_valid_certificates_ci_high": valid_ci["ci_high"],
        "tamper_detection_rate_invalid_certificates": invalid_ci["rate"],
        "tamper_detection_rate_invalid_certificates_ci_low": invalid_ci["ci_low"],
        "tamper_detection_rate_invalid_certificates_ci_high": invalid_ci["ci_high"],
    }
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    payload = run_simulation()
    print(json.dumps(payload, indent=2))
