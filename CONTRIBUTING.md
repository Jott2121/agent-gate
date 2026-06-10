# Contributing to agent-gate

Thanks for your interest in improving agent-gate.

## Setup

```bash
git clone https://github.com/Jott2121/agent-gate && cd agent-gate
pip install -e ".[dev]"
```

## Running tests

```bash
python -m pytest -q
```

Tests must pass on Python 3.11-3.13 (enforced by CI).

## Guidelines

- Keep the core (`agent_gate/gate.py`, `agent_gate/ledger.py`) stdlib-only. The only runtime dependency is `mcp`, confined to `agent_gate/server.py`.
- Add or update tests for any behavior change. MCP tools are tested by calling them, not just importing.
- Keep changes small and focused. One topic per pull request.
- Open an issue first for larger changes so we can discuss the approach.

## Submitting changes

1. Fork the repo and create a feature branch.
2. Make your change with tests.
3. Ensure `python -m pytest -q` passes locally.
4. Open a pull request with a clear description of what changed and why.
