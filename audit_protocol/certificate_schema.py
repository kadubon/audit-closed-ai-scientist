"""Validation utilities for minimal Incorporation Certificate schema."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping


ALLOWED_PHYSICAL_BRANCHES = {"spoofing", "aging", "sentinel_maintenance"}
ALLOWED_PROGRESS_MODES = {"fixed_ips", "variance_adaptive"}
ALLOWED_EXTERNAL_CERT_BITS = {"0", "1", 0, 1}


def _is_dict(value: Any) -> bool:
    return isinstance(value, dict)


def _require_keys(obj: Mapping[str, Any], keys: List[str], path: str, errors: List[str]) -> None:
    for key in keys:
        if key not in obj:
            errors.append(f"missing key: {path}.{key}")


def canonical_certificate_json(certificate: Mapping[str, Any]) -> str:
    return json.dumps(certificate, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def certificate_digest(certificate: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_certificate_json(certificate).encode("utf-8")).hexdigest()


def minimal_certificate_template() -> Dict[str, Any]:
    """Construct a minimal certificate aligned with manuscript Appendix schema."""
    return {
        "genesis": {"G0": "<hash>", "G1": "<hash>", "GHW": "<hash>"},
        "epoch": 0,
        "candidate_set": {"id": "<Cand_t>", "commitment": "<hash>"},
        "selected_candidate": "<cid>",
        "interface": {
            "expansion": {"i": "<spec-hash>", "audit_graph": "<hash>"},
            "witnesses": [],
            "garbling_challenge_seed": "<beacon-seed>",
        },
        "provenance": {
            "attestation": {
                "device_id": "...",
                "firmware": "<hash>",
                "calibration": "<hash>",
                "nonce": "<beacon-derived>",
                "signature": "<sig>",
            }
        },
        "data": {
            "D_eval": "<digest>",
            "role_scheduler": "<hash>",
            "propensity_log_digest": "<digest>",
            "D_fit": "<digest>",
            "D_A": {"digest": "<digest>", "alpha": "alpha_cons"},
            "D_H": {"digest": "<digest>", "alpha": "alpha_prog"},
            "D_P": {"digest": "<digest>", "alpha": "alpha_nov"},
            "D_G": {"digest": "<digest>", "alpha": "alpha_garb"},
        },
        "gates": {
            "coherence": {"eps_coh": "eps_coh", "eps_det": "eps_det", "L_det": "L_det", "path_bounds": []},
            "safety": {},
            "integrity": {"e_process": {}, "e_value": 1.0},
            "physical_coherence": {
                "witnesses": [],
                "e_values": [],
                "branch": "aging",
                "recalibration": {
                    "sentinel_primary_digest": "<digest>",
                    "sentinel_secondary_digest": "<digest>",
                    "theta_old": "<hash>",
                    "theta_new": "<hash>",
                    "threshold_refresh": [],
                },
            },
            "conservativity": {"e_process": {}, "e_value": 1.0},
            "progress": {
                "reference_QP": "...",
                "ips_ratio_cap": "c_w",
                "mode": "fixed_ips",
                "variance_trace_digest": "<digest>",
                "e_process": {},
                "e_value": 1.0,
            },
            "drift": {
                "global_e_process": {},
                "local_subgraph_e_values": [],
                "external_cert_bit": "0",
                "m_ext": 0,
                "kappa_t": 1.0,
            },
            "novelty": {"dual_nu": 0.0, "eligible_cost_trace": [], "slashing_events": [], "e_process": {}, "e_value": 1.0},
        },
    }


def validate_certificate(certificate: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if not _is_dict(certificate):
        return ["certificate must be a JSON object"]

    top_required = ["genesis", "epoch", "candidate_set", "selected_candidate", "interface", "provenance", "data", "gates"]
    _require_keys(certificate, top_required, "certificate", errors)
    if errors:
        return errors

    genesis = certificate["genesis"]
    candidate_set = certificate["candidate_set"]
    interface = certificate["interface"]
    provenance = certificate["provenance"]
    data = certificate["data"]
    gates = certificate["gates"]

    if not isinstance(certificate["epoch"], int) or certificate["epoch"] < 0:
        errors.append("certificate.epoch must be a nonnegative integer")

    if not _is_dict(genesis):
        errors.append("certificate.genesis must be an object")
    else:
        _require_keys(genesis, ["G0", "G1", "GHW"], "certificate.genesis", errors)

    if not _is_dict(candidate_set):
        errors.append("certificate.candidate_set must be an object")
    else:
        _require_keys(candidate_set, ["id", "commitment"], "certificate.candidate_set", errors)

    if not _is_dict(interface):
        errors.append("certificate.interface must be an object")
    else:
        _require_keys(interface, ["expansion", "witnesses", "garbling_challenge_seed"], "certificate.interface", errors)
        if _is_dict(interface.get("expansion", {})):
            _require_keys(interface["expansion"], ["i", "audit_graph"], "certificate.interface.expansion", errors)
        else:
            errors.append("certificate.interface.expansion must be an object")

    if not _is_dict(provenance):
        errors.append("certificate.provenance must be an object")
    else:
        _require_keys(provenance, ["attestation"], "certificate.provenance", errors)
        if _is_dict(provenance.get("attestation", {})):
            _require_keys(
                provenance["attestation"],
                ["device_id", "firmware", "calibration", "nonce", "signature"],
                "certificate.provenance.attestation",
                errors,
            )
        else:
            errors.append("certificate.provenance.attestation must be an object")

    if not _is_dict(data):
        errors.append("certificate.data must be an object")
    else:
        _require_keys(data, ["D_eval", "role_scheduler", "propensity_log_digest", "D_fit", "D_A", "D_H", "D_P", "D_G"], "certificate.data", errors)
        for tag in ["D_A", "D_H", "D_P", "D_G"]:
            block = data.get(tag)
            if not _is_dict(block):
                errors.append(f"certificate.data.{tag} must be an object")
                continue
            _require_keys(block, ["digest", "alpha"], f"certificate.data.{tag}", errors)

    if not _is_dict(gates):
        errors.append("certificate.gates must be an object")
    else:
        _require_keys(
            gates,
            ["coherence", "safety", "integrity", "physical_coherence", "conservativity", "progress", "drift", "novelty"],
            "certificate.gates",
            errors,
        )
        physical = gates.get("physical_coherence", {})
        if _is_dict(physical):
            _require_keys(physical, ["witnesses", "e_values", "branch", "recalibration"], "certificate.gates.physical_coherence", errors)
            if "branch" in physical and physical["branch"] not in ALLOWED_PHYSICAL_BRANCHES:
                errors.append(
                    f"certificate.gates.physical_coherence.branch must be one of {sorted(ALLOWED_PHYSICAL_BRANCHES)}"
                )
        else:
            errors.append("certificate.gates.physical_coherence must be an object")

        progress = gates.get("progress", {})
        if _is_dict(progress):
            _require_keys(progress, ["reference_QP", "ips_ratio_cap", "mode", "variance_trace_digest", "e_process", "e_value"], "certificate.gates.progress", errors)
            if "mode" in progress and progress["mode"] not in ALLOWED_PROGRESS_MODES:
                errors.append(f"certificate.gates.progress.mode must be one of {sorted(ALLOWED_PROGRESS_MODES)}")
        else:
            errors.append("certificate.gates.progress must be an object")

        drift = gates.get("drift", {})
        if _is_dict(drift):
            _require_keys(drift, ["global_e_process", "local_subgraph_e_values", "external_cert_bit", "m_ext", "kappa_t"], "certificate.gates.drift", errors)
            if "external_cert_bit" in drift and drift["external_cert_bit"] not in ALLOWED_EXTERNAL_CERT_BITS:
                errors.append("certificate.gates.drift.external_cert_bit must be 0 or 1")
        else:
            errors.append("certificate.gates.drift must be an object")

    return errors


def validate_certificate_or_raise(certificate: Mapping[str, Any]) -> None:
    errors = validate_certificate(certificate)
    if errors:
        raise ValueError("certificate validation failed: " + "; ".join(errors))


def validate_certificate_and_digest(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    errors = validate_certificate(certificate)
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "digest": certificate_digest(certificate) if len(errors) == 0 else None,
    }
