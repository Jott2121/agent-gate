"""
agent-gate demo — run this to see fail-closed gating and hash-chained receipts in action.

    pip install mcp-agent-gate
    python examples/demo.py
"""

import json
import tempfile
import os
from agent_gate.gate import DEFAULT_SHIP_GATE
from agent_gate.ledger import Ledger

SEP = "-" * 60

# --- 1. Agent tries to ship with incomplete evidence ---
print(SEP)
print("1. Agent claims done — but two checks are missing")
print(SEP)

result = DEFAULT_SHIP_GATE.evaluate({
    "deterministic_checks_pass": True,
    "independent_refute_review": True,
    "no_secrets": True,
    # human_gated_if_irreversible: not provided  ->  fail-closed
    # honest_receipt_logged: not provided         ->  fail-closed
})
print(json.dumps({"passed": result.passed, "blocking": result.blocking}, indent=2))

# --- 2. Agent satisfies all checks ---
print()
print(SEP)
print("2. Agent satisfies all five checks")
print(SEP)

result2 = DEFAULT_SHIP_GATE.evaluate({
    "deterministic_checks_pass": True,
    "independent_refute_review": True,
    "no_secrets": True,
    "human_gated_if_irreversible": True,
    "honest_receipt_logged": True,
})
print(json.dumps({"passed": result2.passed, "blocking": result2.blocking}, indent=2))

# --- 3. Record a tamper-evident receipt ---
print()
print(SEP)
print("3. Record a hash-chained receipt")
print(SEP)

tmp = tempfile.mktemp(suffix=".jsonl")
led = Ledger(tmp)

r1 = led.append(decision="ship v0.1", metric="gate", value="passed", verdict="shipped")
r2 = led.append(decision="deploy", metric="human_approval", value="yes", verdict="approved")

for r in [r1, r2]:
    print(json.dumps({
        "seq": r["seq"],
        "decision": r["decision"],
        "verdict": r["verdict"],
        "hash": r["hash"][:16] + "...",
    }, indent=2))

# --- 4. Verify the chain is intact ---
print()
print(SEP)
print("4. Verify the chain — edit receipts.jsonl to see this flip to False")
print(SEP)
print("chain_intact:", led.verify_chain())

os.unlink(tmp)
print()
print("Done. Install: pip install mcp-agent-gate")
