"""Audit-closed update logic: Accept_t is a deterministic function of public log."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Dict, Iterable, List

import numpy as np

from audit_protocol.e_process import DEFAULT_LAMBDAS
from audit_protocol.sequential_tests import AlphaSpendingSchedule, run_grid_e_test
from audit_protocol.transparency_log import LogEntry, TransparencyLog, expected_entry_hash
from baseline_ai_scientist.experiment_runner import prepare_candidate_increment_stream
from baseline_ai_scientist.hypothesis_generator import CandidateModel


@dataclass
class AuditClosedConfig:
    total_alpha: float = 0.05
    alpha_decay: float = 0.5
    lambdas: tuple[float, ...] = DEFAULT_LAMBDAS
    train_fraction: float = 0.4
    clip_bound: float = 2.0


def _entry_payload(entry: LogEntry | Dict[str, Any]) -> Dict[str, Any]:
    return entry.payload if isinstance(entry, LogEntry) else entry["payload"]


def _entry_type(entry: LogEntry | Dict[str, Any]) -> str:
    return entry.event_type if isinstance(entry, LogEntry) else entry["event_type"]


def _entry_index(entry: LogEntry | Dict[str, Any]) -> int | None:
    return entry.index if isinstance(entry, LogEntry) else entry.get("index")


def _entry_prev_hash(entry: LogEntry | Dict[str, Any]) -> str | None:
    return entry.prev_hash if isinstance(entry, LogEntry) else entry.get("prev_hash")


def _entry_hash(entry: LogEntry | Dict[str, Any]) -> str | None:
    return entry.entry_hash if isinstance(entry, LogEntry) else entry.get("entry_hash")


def _verify_hash_chain(entries: List[LogEntry | Dict[str, Any]]) -> bool:
    prev_hash = "GENESIS"
    for idx, entry in enumerate(entries):
        if _entry_index(entry) != idx:
            return False
        if _entry_prev_hash(entry) != prev_hash:
            return False
        entry_hash = _entry_hash(entry)
        if entry_hash is None:
            return False
        expected = expected_entry_hash(
            index=idx,
            event_type=_entry_type(entry),
            payload=_entry_payload(entry),
            prev_hash=prev_hash,
        )
        if entry_hash != expected:
            return False
        prev_hash = entry_hash
    return True


def acceptance_from_public_log(
    log_entries: Iterable[LogEntry | Dict[str, Any]],
    epoch: int,
    total_alpha: float | None = None,
    alpha_decay: float | None = None,
    require_complete_evaluations: bool = True,
    require_hash_chain_integrity: bool = True,
) -> Dict[str, Any]:
    """Deterministic decision function using only logged artifacts."""
    entries = list(log_entries)
    if require_hash_chain_integrity and not _verify_hash_chain(entries):
        raise ValueError("log hash-chain integrity verification failed")
    genesis_entries = [_entry_payload(entry) for entry in entries if _entry_type(entry) == "genesis"]
    if not genesis_entries:
        raise ValueError("missing genesis entry")
    genesis = genesis_entries[0]
    log_total_alpha = float(genesis["total_alpha"])
    log_alpha_decay = float(genesis["alpha_decay"])
    total_alpha = log_total_alpha if total_alpha is None else float(total_alpha)
    alpha_decay = log_alpha_decay if alpha_decay is None else float(alpha_decay)
    if not np.isclose(total_alpha, log_total_alpha):
        raise ValueError("provided total_alpha does not match logged genesis total_alpha")
    if not np.isclose(alpha_decay, log_alpha_decay):
        raise ValueError("provided alpha_decay does not match logged genesis alpha_decay")

    commitments = [
        _entry_payload(entry)
        for entry in entries
        if _entry_type(entry) == "candidate_commitment" and _entry_payload(entry).get("epoch") == epoch
    ]
    if len(commitments) != 1:
        raise ValueError(f"missing candidate commitment for epoch={epoch}")

    commitment = commitments[0]
    candidate_names = list(commitment["candidate_names"])
    candidate_count = len(candidate_names)
    if candidate_count == 0:
        raise ValueError("candidate commitment must contain at least one candidate")
    if len(set(candidate_names)) != candidate_count:
        raise ValueError("candidate commitment contains duplicate candidate names")

    evaluations: Dict[str, float] = {}
    evaluation_counts: Dict[str, int] = {name: 0 for name in candidate_names}
    for entry in entries:
        if _entry_type(entry) != "candidate_evaluation":
            continue
        payload = _entry_payload(entry)
        if payload.get("epoch") != epoch:
            continue
        name = payload.get("candidate_name")
        if name not in evaluation_counts:
            raise ValueError(f"candidate_evaluation references uncommitted candidate: {name}")
        evaluation_counts[name] += 1
        if evaluation_counts[name] > 1:
            raise ValueError(f"duplicate candidate_evaluation detected for candidate: {name}")
        # Transcript consistency checks are fail-closed.
        payload_alpha_epoch = payload.get("alpha_epoch")
        payload_batch_threshold = payload.get("batch_threshold")
        if payload_alpha_epoch is None or payload_batch_threshold is None:
            raise ValueError(f"incomplete evaluation transcript for candidate={name}")
        if float(payload_alpha_epoch) <= 0.0:
            raise ValueError(f"invalid alpha_epoch in evaluation transcript for candidate={name}")
        evaluations[name] = float(payload["final_e_value"])

    if require_complete_evaluations:
        missing = [name for name, count in evaluation_counts.items() if count == 0]
        if missing:
            raise ValueError(f"incomplete candidate evaluations for epoch={epoch}, missing={missing[:5]}")

    schedule = AlphaSpendingSchedule(total_alpha=total_alpha, decay=alpha_decay)
    alpha_epoch = schedule.alpha_for_epoch(epoch)
    threshold = candidate_count / alpha_epoch
    for entry in entries:
        if _entry_type(entry) != "candidate_evaluation":
            continue
        payload = _entry_payload(entry)
        if payload.get("epoch") != epoch:
            continue
        if not np.isclose(float(payload["alpha_epoch"]), alpha_epoch):
            raise ValueError("candidate evaluation alpha_epoch does not match logged genesis schedule")
        if not np.isclose(float(payload["batch_threshold"]), threshold):
            raise ValueError("candidate evaluation batch_threshold does not match computed threshold")

    ranked = sorted(
        (
            {"candidate_name": name, "final_e_value": value}
            for name, value in evaluations.items()
        ),
        key=lambda item: (-item["final_e_value"], item["candidate_name"]),
    )

    winner = ranked[0] if ranked else {"candidate_name": None, "final_e_value": 0.0}
    accepted = bool(winner["candidate_name"] is not None and winner["final_e_value"] >= threshold)

    return {
        "epoch": epoch,
        "alpha_epoch": alpha_epoch,
        "threshold": threshold,
        "candidate_count": candidate_count,
        "evaluated_count": len(ranked),
        "winner": winner["candidate_name"],
        "winner_e_value": float(winner["final_e_value"]),
        "accepted": accepted,
        "decision_rule": "accept iff max_e_value >= m/alpha_epoch",
    }


class AuditClosedScientist:
    """Audit-closed scientist with deterministic replay and public log governance."""

    def __init__(self, config: AuditClosedConfig | None = None, seed: int = 0) -> None:
        self.config = config or AuditClosedConfig()
        self.rng = np.random.default_rng(seed)
        self.log = TransparencyLog()
        self.log.append(
            "genesis",
            {
                "total_alpha": self.config.total_alpha,
                "alpha_decay": self.config.alpha_decay,
                "lambdas": list(self.config.lambdas),
                "train_fraction": self.config.train_fraction,
                "clip_bound": self.config.clip_bound,
            },
        )

    def evaluate_epoch(
        self,
        epoch: int,
        candidates: List[CandidateModel],
        x: np.ndarray,
        y: np.ndarray,
        stop_on_threshold: bool = True,
    ) -> Dict[str, Any]:
        if epoch < 0:
            raise ValueError("epoch must be nonnegative")
        candidate_names = [candidate.name for candidate in candidates]
        if len(candidate_names) == 0:
            raise ValueError("at least one candidate is required")
        if len(set(candidate_names)) != len(candidate_names):
            raise ValueError("candidate names must be unique per epoch")

        data_digest = hashlib.sha256(
            json.dumps(
                {
                    "x": np.asarray(x, dtype=float).tolist(),
                    "y": np.asarray(y, dtype=float).tolist(),
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        self.log.append(
            "candidate_commitment",
            {
                "epoch": epoch,
                "candidate_names": candidate_names,
                "candidate_count": len(candidate_names),
                "data_digest": data_digest,
            },
        )

        alpha_epoch = AlphaSpendingSchedule(
            total_alpha=self.config.total_alpha,
            decay=self.config.alpha_decay,
        ).alpha_for_epoch(epoch)
        n_candidates = len(candidates)

        for candidate in candidates:
            prepared = prepare_candidate_increment_stream(
                candidate,
                x=x,
                y=y,
                train_fraction=self.config.train_fraction,
                clip_bound=self.config.clip_bound,
            )
            increments = np.asarray(prepared["increments"], dtype=float)
            test_result = run_grid_e_test(
                increments=increments,
                alpha_epoch=alpha_epoch,
                n_candidates=n_candidates,
                lambdas=self.config.lambdas,
                stop_on_threshold=stop_on_threshold,
            )
            self.log.append(
                "candidate_evaluation",
                {
                    "epoch": epoch,
                    "candidate_name": candidate.name,
                    "final_e_value": test_result.final_e_value,
                    "crossed_threshold": test_result.crossed_threshold,
                    "stopping_time": test_result.stopping_time,
                    "trajectory_length": int(len(test_result.trajectory)),
                    "mean_improvement": float(prepared["mean_improvement"]),
                    "mean_increment": float(prepared["mean_increment"]),
                    "alpha_epoch": float(alpha_epoch),
                    "batch_threshold": float(test_result.threshold),
                },
            )

        decision = acceptance_from_public_log(
            self.log.entries,
            epoch=epoch,
            total_alpha=self.config.total_alpha,
            alpha_decay=self.config.alpha_decay,
        )
        self.log.append("epoch_decision", decision)
        return decision

    def replay_epoch(self, epoch: int) -> Dict[str, Any]:
        replayed = acceptance_from_public_log(
            self.log.entries,
            epoch=epoch,
            total_alpha=self.config.total_alpha,
            alpha_decay=self.config.alpha_decay,
        )
        logged = None
        for entry in self.log.entries:
            if entry.event_type == "epoch_decision" and entry.payload.get("epoch") == epoch:
                logged = entry.payload
        if logged is None:
            return {"epoch": epoch, "replay_matches": False, "reason": "missing_logged_decision"}

        keys = [
            "accepted",
            "winner",
            "winner_e_value",
            "threshold",
            "candidate_count",
            "evaluated_count",
            "alpha_epoch",
        ]
        replay_matches = all(np.isclose(replayed[k], logged[k]) if isinstance(replayed[k], float) else replayed[k] == logged[k] for k in keys)

        return {
            "epoch": epoch,
            "replay_matches": bool(replay_matches),
            "replayed": replayed,
            "logged": logged,
            "log_integrity_ok": self.log.verify_integrity(),
        }
