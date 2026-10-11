# .cursor/BUGBOT.md — review rules for agent-gate
# (Bugbot does NOT read .cursor/rules/*.mdc; it reads this file.)

Flag as **blocking**:
1. Any guard, gate, validator, or refusal path that now fails OPEN (returns allow/True/answer on exception, timeout, empty, or malformed input). `Gate.evaluate` must stay fail-closed: only literal `True` satisfies a check.
2. Lowered thresholds: `--cov-fail-under` (the floor is 90), mutation score floors, MIN_SCORE-style constants, retry/timeout bounds removed.
3. Tests that were deleted, skipped, xfailed, or had assertions weakened without a stated reason in the PR body. `tests/test_server.py` may skip only when the `mcp` SDK is absent; a present SDK must not be skipped.
4. README/docs numbers that changed without a reproducing command or artifact in the PR.
5. Any content that looks like employer/corporate data: an employer's name or its abbreviations, internal acronyms, program or site names, classification or export-control markings, real-looking employee records, internal URLs. This repo is personal work only; there are no allowed mentions. Also block any plain-text blocked term added to `.github/blocked-terms.sha256`, and any change that excludes paths from `scripts/scan_blocked_terms.py` or lets it pass when the hash file is missing or empty.
6. Secrets, tokens, `.env` files, or absolute personal paths committed.
7. Unpinned GitHub Actions (must be full SHA) or widened workflow `permissions:`.
8. Live network / model calls added to the default test path.

Flag as **non-blocking**:
- New runtime dependency without justification, or `mcp` imported outside `agent_gate/server.py`.
- Non-deterministic code in eval paths (unseeded RNG, unordered iteration in hashes/output).
- Exceptions swallowed in non-decision code.

Do not comment on: formatting nits or naming bikesheds. This repo has no ruff config.
