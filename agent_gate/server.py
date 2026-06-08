"""agent-gate MCP server — Fleet Mode as tools an AI agent can call on itself.

Exposes four tools over MCP so an agent can gate its own work before claiming
'done': read the checklist, verify evidence against it (fail-closed), and write
tamper-evident honest receipts. The logic lives in the tested, dependency-free
core (`gate.py`, `ledger.py`); this module is the thin MCP adapter.

Run:  python -m agent_gate.server      (stdio transport; add to your MCP client config)
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from agent_gate import gate as G
from agent_gate.ledger import Ledger

mcp = FastMCP("agent-gate")


def _ledger_path() -> str:
    path = os.environ.get("AGENT_GATE_LEDGER") or os.path.expanduser("~/.agent-gate/receipts.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


@mcp.tool()
def gate_checklist(name: str = "ship") -> dict:
    """Return the checklist an agent must satisfy before it may claim a task done."""
    g = G.get_gate(name)
    return {"gate": g.name, "checks": g.checks}


@mcp.tool()
def verify_gate(evidence: dict, name: str = "ship") -> dict:
    """Evaluate evidence against a gate. FAIL-CLOSED: a check is satisfied only if
    its value is exactly true; anything missing or non-true blocks. Returns
    {"passed": bool, "blocking": [check_ids]}."""
    return G.get_gate(name).evaluate(evidence).as_dict()


@mcp.tool()
def record_receipt(decision: str, metric: str, value: str, verdict: str) -> dict:
    """Append an honest, hash-chained receipt to the ledger and return it.
    verdict is typically one of: kept, killed, shipped, blocked."""
    return Ledger(_ledger_path()).append(decision=decision, metric=metric, value=value, verdict=verdict)


@mcp.tool()
def read_receipts() -> dict:
    """Return every receipt plus whether the hash chain is intact (tamper-evident)."""
    led = Ledger(_ledger_path())
    return {"receipts": led.read_all(), "chain_intact": led.verify_chain()}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
