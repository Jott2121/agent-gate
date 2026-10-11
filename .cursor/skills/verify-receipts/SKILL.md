---
name: verify-receipts
description: Use before opening or updating a PR, or when README/docs numbers change. Re-runs agent-gate's tests and receipt check, cross-checks published claims, and writes a receipts block for the PR body.
---
# Verify receipts

1. Read AGENTS.md "Commands". From the repo root, run:
   - `pip install -e ".[dev]" pytest-cov`
   - Tests, including the coverage gate (do not lower 90): `python -m pytest -q --cov=agent_gate --cov-report=term-missing --cov-fail-under=90`
   - Receipts: `python scripts/check_receipts.py`
   - Lint and typecheck: n/a. There is no ruff or mypy config, no `eval/` harness, and no `--check` scorer.
   Capture exit codes and the last ~20 lines of each.
2. `git diff origin/main -- README.md docs/ WRITEUP.md` — list every number that changed. For each, find the command that produces it and re-run it. If you can't reproduce it, mark it UNVERIFIED and stop; do not open the PR as ready.
   Known gap: README says "currently 97% covered". `scripts/check_receipts.py` prints the percentage from the pytest command above. If they differ, report both. Leave the sentence alone unless the PR's purpose is to update that published number.
   The `16.7%` sentence cites sabot. Do not recompute it in this repo.
   Demo hash prefixes in the README are not stable receipts. Ledger hashes include a timestamp.
3. Grep the diff for employer-data and secret patterns (see `.cursor/rules/40-security-and-data.mdc`). The README `## About` author bio is the only allowed hit. Any other hit means stop and report.
4. Confirm `--cov-fail-under=90` is unchanged and no tests were skipped, xfailed, or removed.
5. Output a Markdown block:
   - Commands run + pass/fail
   - Numbers: before → after → command → reproduced? (Y/N)
   - Not verified / known gaps
6. Paste that block into the PR's "How verified" section. Never claim a check passed that you didn't run.
