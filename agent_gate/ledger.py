"""Append-only, hash-chained receipts ledger — tamper-evident "honest receipts".

Each receipt records a decision + a metric + value + verdict, and is linked to
the previous receipt via a sha256 chain. Editing or deleting any past receipt
breaks the chain, so `verify_chain()` proves the log is intact. Stdlib only.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os

GENESIS = "0" * 64

# Fields that are hashed, in a fixed order (so the hash is reproducible).
_HASHED = ("seq", "ts", "decision", "metric", "value", "verdict", "prev_hash")


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash(entry: dict) -> str:
    payload = json.dumps([entry[f] for f in _HASHED], separators=(",", ":"), sort_keys=False)
    return hashlib.sha256(payload.encode()).hexdigest()


class Ledger:
    """A receipts ledger. `path=":memory:"` keeps it in RAM; any other path is an
    append-only JSONL file that is loaded on open and appended to on write."""

    def __init__(self, path: str = ":memory:", clock=_utc_now):
        self.path = path
        self._clock = clock
        self._entries: list[dict] = []
        if path != ":memory:" and os.path.exists(path):
            with open(path) as f:
                self._entries = [json.loads(line) for line in f if line.strip()]

    def append(self, *, decision: str, metric: str, value, verdict: str) -> dict:
        prev_hash = self._entries[-1]["hash"] if self._entries else GENESIS
        entry = {
            "seq": len(self._entries) + 1,
            "ts": self._clock(),
            "decision": decision,
            "metric": metric,
            "value": value,
            "verdict": verdict,
            "prev_hash": prev_hash,
        }
        entry["hash"] = _hash(entry)
        self._entries.append(entry)
        if self.path != ":memory:":
            with open(self.path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        return entry

    def read_all(self) -> list[dict]:
        return list(self._entries)

    def verify_chain(self) -> bool:
        prev = GENESIS
        for i, entry in enumerate(self._entries, start=1):
            if entry.get("seq") != i or entry.get("prev_hash") != prev:
                return False
            recomputed = _hash({k: entry.get(k) for k in _HASHED})
            if recomputed != entry.get("hash"):
                return False
            prev = entry["hash"]
        return True
