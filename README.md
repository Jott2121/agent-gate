![agent-gate — gate an AI agent's work before it ships: deterministic checks, refute-first review, tamper-evident receipts](assets/banner.png)

# agent-gate

[![ci](https://github.com/Jott2121/agent-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/Jott2121/agent-gate/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-server-blueviolet.svg)](https://modelcontextprotocol.io/)

**An MCP server that lets an AI agent gate its own work before it claims "done" — deterministic checks → independent refute-first review → a tamper-evident honest receipt.**

Agents that grade their own homework ship slop. `agent-gate` turns that discipline into tools an agent must actually pass: a **fail-closed** checklist and an **append-only, hash-chained** receipts ledger. It's [Fleet Mode](https://github.com/Jott2121/bow) — my agent-orchestration doctrine — made into a runnable tool. Receipts over hype, enforced by the data structures.

```text
agent: "done!"  →  verify_gate(evidence)  →  { passed: false, blocking: ["independent_refute_review", "no_secrets"] }
```

## Why

The expensive failures in agent systems are the silent ones: a model update degrades output, a change quietly breaks a workflow, an agent declares success while the work is wrong. The fix isn't a smarter model — it's a gate the agent can't talk its way past:

- **Fail-closed.** A check counts as satisfied only if it's *explicitly* true. Missing proof is not proof. (Mirrors a promotion gate, not a vibe check.)
- **Tamper-evident receipts.** Every decision is recorded as `(decision, metric, value, verdict)` linked into a sha256 chain. Edit or delete any past receipt and `verify_chain()` returns false. The honest log is enforced by the structure, not by good intentions.
- **Human-gated by default.** "Any irreversible/outward act got human approval" is a required check — agents draft, humans approve.

## Tools (over MCP)

| Tool | What it does |
|---|---|
| `gate_checklist(name="ship")` | Returns the checklist the agent must satisfy before claiming done. |
| `verify_gate(evidence, name="ship")` | Evaluates evidence **fail-closed** → `{passed, blocking}`. |
| `record_receipt(decision, metric, value, verdict)` | Appends an honest, hash-chained receipt; returns it. |
| `read_receipts()` | Returns every receipt + whether the chain is intact. |

The default **`ship` gate** encodes Fleet Mode: `deterministic_checks_pass`, `independent_refute_review`, `no_secrets`, `human_gated_if_irreversible`, `honest_receipt_logged`.

## Install & wire into an MCP client

```bash
pip install -e .          # or: pip install agent-gate
```

Add it to your MCP client (Claude Desktop / Claude Code) config:

```json
{
  "mcpServers": {
    "agent-gate": { "command": "python", "args": ["-m", "agent_gate.server"] }
  }
}
```

Now your agent can call `verify_gate(...)` before it tells you it's finished — and you get a tamper-evident trail of what it decided. Receipts persist to `~/.agent-gate/receipts.jsonl` (override with `AGENT_GATE_LEDGER`).

## Use it directly (no MCP client needed)

```python
from agent_gate.gate import DEFAULT_SHIP_GATE
from agent_gate.ledger import Ledger

res = DEFAULT_SHIP_GATE.evaluate({
    "deterministic_checks_pass": True,
    "independent_refute_review": True,
    "no_secrets": True,
    "human_gated_if_irreversible": True,
    # honest_receipt_logged missing  →  fail-closed
})
print(res.passed, res.blocking)   # False ['honest_receipt_logged']

led = Ledger("receipts.jsonl")
led.append(decision="ship v0.1", metric="tests", value="17", verdict="shipped")
print(led.verify_chain())         # True  (until someone edits the log)
```

## Design

- **Tested, dependency-free core.** `agent_gate/gate.py` (fail-closed checklist) and `agent_gate/ledger.py` (hash-chained receipts) are pure stdlib — fast to read, fast to trust. `agent_gate/server.py` is a thin MCP adapter over them.
- **17 tests, CI on Python 3.11–3.13.** The MCP tools are tested by *calling them*, not just importing.

## Tests

```bash
pip install -e ".[dev]" && python -m pytest -q
```

## About

Built by **Jeff Otterson** ([Jott2121](https://github.com/Jott2121)). `agent-gate` operationalizes the gating discipline from [**bow**](https://github.com/Jott2121/bow) (an autonomous all-Claude chief-of-staff agent) and the **Fleet Mode** doctrine. MIT licensed.
