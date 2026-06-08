"""The ship-gate — Fleet Mode encoded as an enforceable, fail-closed checklist.

A Gate is a named list of checks. `evaluate(evidence)` passes ONLY if every
check is explicitly satisfied (literal True); anything missing or non-True is
blocking. Fail-closed by design: the absence of proof is not proof. This turns
"deterministic checks → independent refute-first review → honest receipt" from a
good intention into something a tool can refuse to let an agent skip.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GateResult:
    passed: bool
    blocking: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"passed": self.passed, "blocking": self.blocking}


class Gate:
    def __init__(self, name: str, checks: list[dict]):
        self.name = name
        self.checks = checks

    def evaluate(self, evidence: dict) -> GateResult:
        blocking = [c["id"] for c in self.checks if evidence.get(c["id"]) is not True]
        return GateResult(passed=not blocking, blocking=blocking)


# The default gate: Fleet Mode's discipline, every check required.
DEFAULT_SHIP_GATE = Gate(
    "ship",
    [
        {"id": "deterministic_checks_pass",
         "description": "All deterministic checks are green (tests, linters, type-checks, build)."},
        {"id": "independent_refute_review",
         "description": "An independent, refute-first review ran and did not block (no agent grades its own work)."},
        {"id": "no_secrets",
         "description": "A secret/credential scan of the change is clean."},
        {"id": "human_gated_if_irreversible",
         "description": "Any irreversible or outward-facing act (deploy, send, publish, delete, spend) got explicit human approval."},
        {"id": "honest_receipt_logged",
         "description": "A receipt recording the real metric and verdict was written to the ledger."},
    ],
)

GATES = {DEFAULT_SHIP_GATE.name: DEFAULT_SHIP_GATE}


def get_gate(name: str = "ship") -> Gate:
    if name not in GATES:
        raise ValueError(f"unknown gate {name!r}; known: {sorted(GATES)}")
    return GATES[name]
