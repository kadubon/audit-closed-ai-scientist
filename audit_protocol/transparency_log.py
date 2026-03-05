"""Append-only transparency log with hash chaining and checkpoint roots."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Dict, List


def canonical_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _entry_digest(index: int, event_type: str, payload: Dict[str, Any], prev_hash: str) -> str:
    material = canonical_json(
        {
            "index": index,
            "event_type": event_type,
            "payload": payload,
            "prev_hash": prev_hash,
        }
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def expected_entry_hash(index: int, event_type: str, payload: Dict[str, Any], prev_hash: str) -> str:
    """Public wrapper for deterministic entry-hash calculation."""
    return _entry_digest(index=index, event_type=event_type, payload=payload, prev_hash=prev_hash)


@dataclass
class LogEntry:
    index: int
    timestamp_utc: str
    event_type: str
    payload: Dict[str, Any]
    prev_hash: str
    entry_hash: str


class TransparencyLog:
    """Tamper-evident log for deterministic decision replay.

    Security model:
    - Hash chaining makes in-log entry edits detectable.
    - Merkle root checkpoints make omission/reordering detectable.
    - Optional HMAC checkpoint signatures support witness-side anchoring.
    """

    def __init__(self) -> None:
        self.entries: List[LogEntry] = []

    def append(self, event_type: str, payload: Dict[str, Any]) -> LogEntry:
        prev_hash = self.entries[-1].entry_hash if self.entries else "GENESIS"
        index = len(self.entries)
        entry_hash = _entry_digest(index, event_type, payload, prev_hash)
        entry = LogEntry(
            index=index,
            timestamp_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            event_type=event_type,
            payload=payload,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        self.entries.append(entry)
        return entry

    def verify_integrity(self) -> bool:
        prev_hash = "GENESIS"
        for idx, entry in enumerate(self.entries):
            if entry.index != idx:
                return False
            expected = _entry_digest(idx, entry.event_type, entry.payload, prev_hash)
            if entry.entry_hash != expected:
                return False
            prev_hash = entry.entry_hash
        return True

    def merkle_root(self) -> str:
        """Compute Merkle root over entry hashes."""
        if not self.entries:
            return hashlib.sha256(b"EMPTY_LOG").hexdigest()

        level = [bytes.fromhex(entry.entry_hash) for entry in self.entries]
        while len(level) > 1:
            if len(level) % 2 == 1:
                level.append(level[-1])
            next_level = []
            for i in range(0, len(level), 2):
                next_level.append(hashlib.sha256(level[i] + level[i + 1]).digest())
            level = next_level
        return level[0].hex()

    def checkpoint(self, anchor: str = "", secret: str | None = None) -> Dict[str, Any]:
        """Create an auditable checkpoint record.

        If `secret` is provided, returns an HMAC signature over the checkpoint payload.
        This can be used by an external witness service to anchor log roots.
        """
        payload: Dict[str, Any] = {
            "entry_count": len(self.entries),
            "head_hash": self.entries[-1].entry_hash if self.entries else "GENESIS",
            "merkle_root": self.merkle_root(),
            "anchor": anchor,
            "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
        if secret is not None:
            message = canonical_json(payload).encode("utf-8")
            payload["hmac_sha256"] = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return payload

    def to_serializable(self) -> List[Dict[str, Any]]:
        return [asdict(entry) for entry in self.entries]

    def save_json(self, path: str | Path, anchor: str = "") -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = self.checkpoint(anchor=anchor)
        payload = {
            "integrity_ok": self.verify_integrity(),
            "checkpoint": checkpoint,
            "entries": self.to_serializable(),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def verify_serialized_payload(payload: Dict[str, Any]) -> bool:
        log = TransparencyLog()
        for raw in payload.get("entries", []):
            log.entries.append(LogEntry(**raw))
        if not log.verify_integrity():
            return False
        checkpoint = payload.get("checkpoint", {})
        if not checkpoint:
            return False
        expected_root = log.merkle_root()
        expected_head = log.entries[-1].entry_hash if log.entries else "GENESIS"
        return (
            checkpoint.get("entry_count") == len(log.entries)
            and checkpoint.get("head_hash") == expected_head
            and checkpoint.get("merkle_root") == expected_root
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "TransparencyLog":
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        if not cls.verify_serialized_payload(loaded):
            raise ValueError(f"serialized log failed integrity verification: {path}")
        log = cls()
        for raw in loaded.get("entries", []):
            log.entries.append(LogEntry(**raw))
        return log
