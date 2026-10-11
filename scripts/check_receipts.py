#!/usr/bin/env python3
"""Recompute the published claims this repo can actually reproduce.

Fails when the fail-closed README examples drift, when the CI coverage floor
is no longer ``--cov-fail-under=90``, or when measured coverage drops below
that floor.

The README sentence "currently 97% covered" is a published number. This script
prints the measured percentage beside it and does not rewrite README. A claim
other than that existing 97, that also disagrees with the measurement, fails
the job. See AGENTS.md.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COVERAGE_FLOOR = 90
# Published README sentence. Left in place on purpose; do not bump this to
# "fix" a measurement gap inside an unrelated change.
PUBLISHED_COVERAGE_CLAIM = 97

README_MUST_CONTAIN = (
    "False ['honest_receipt_logged']",
    '"human_gated_if_irreversible"',
    '"honest_receipt_logged"',
    '"passed": true',
    '"blocking": []',
    "16.7%",
    "sabot",
)


def _fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def _check_gate_examples() -> None:
    from agent_gate.gate import DEFAULT_SHIP_GATE

    partial = DEFAULT_SHIP_GATE.evaluate(
        {
            "deterministic_checks_pass": True,
            "independent_refute_review": True,
            "no_secrets": True,
            "human_gated_if_irreversible": True,
        }
    )
    if partial.passed is not False or partial.blocking != ["honest_receipt_logged"]:
        _fail(
            "README quickstart example drifted: "
            f"passed={partial.passed} blocking={partial.blocking}"
        )

    missing_two = DEFAULT_SHIP_GATE.evaluate(
        {
            "deterministic_checks_pass": True,
            "independent_refute_review": True,
            "no_secrets": True,
        }
    )
    if missing_two.passed is not False or missing_two.blocking != [
        "human_gated_if_irreversible",
        "honest_receipt_logged",
    ]:
        _fail(
            "README demo section 1 drifted: "
            f"passed={missing_two.passed} blocking={missing_two.blocking}"
        )

    satisfied = DEFAULT_SHIP_GATE.evaluate(
        {check["id"]: True for check in DEFAULT_SHIP_GATE.checks}
    )
    if satisfied.passed is not True or satisfied.blocking != []:
        _fail(
            "README demo section 2 drifted: "
            f"passed={satisfied.passed} blocking={satisfied.blocking}"
        )
    print("gate examples: match README (fail-closed ship gate)")


def _check_readme_text() -> int:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for snippet in README_MUST_CONTAIN:
        if snippet not in readme:
            _fail(f"README is missing published snippet: {snippet}")
    match = re.search(r"currently (\d+)% covered", readme)
    if match is None:
        _fail('README is missing the "currently N% covered" sentence')
    claimed = int(match.group(1))
    print(f"readme coverage sentence: currently {claimed}% covered")
    print("external citation: 16.7% remains attributed in the sabot paragraph (not recomputed here)")
    return claimed


def _check_coverage_floor() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    if f"--cov-fail-under={COVERAGE_FLOOR}" not in ci:
        _fail(f"CI coverage gate is no longer --cov-fail-under={COVERAGE_FLOOR}")
    other = re.findall(r"--cov-fail-under=(\d+)", ci)
    if other != [str(COVERAGE_FLOOR)]:
        _fail(f"unexpected coverage floors in ci.yml: {other}")
    print(f"ci coverage floor: --cov-fail-under={COVERAGE_FLOOR}")


def _measure_coverage() -> tuple[int, str]:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--cov=agent_gate",
            "--cov-report=term-missing",
            f"--cov-fail-under={COVERAGE_FLOOR}",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = proc.stdout + "\n" + proc.stderr
    if proc.returncode != 0:
        print(output)
        _fail(f"pytest coverage gate failed (exit {proc.returncode})")
    rounded = re.search(r"^TOTAL\s+\d+\s+\d+\s+(\d+)%", output, re.M)
    exact = re.search(r"Total coverage:\s+([0-9.]+)%", output)
    if rounded is None or exact is None:
        print(output)
        _fail("could not parse coverage from pytest output")
    print(f"measured coverage: {exact.group(1)}% (report rounds to {rounded.group(1)}%)")
    return int(rounded.group(1)), exact.group(1)


def main() -> None:
    _check_gate_examples()
    claimed = _check_readme_text()
    _check_coverage_floor()
    measured, exact = _measure_coverage()
    if claimed == measured:
        print(f"coverage receipt: README {claimed}% matches measured {measured}%")
        return
    if claimed == PUBLISHED_COVERAGE_CLAIM:
        print(
            "NOTE: README says currently "
            f"{claimed}% covered; this run measured {exact}% "
            f"(report {measured}%). Published sentence left unchanged."
        )
        return
    _fail(
        f"README coverage claim {claimed}% does not match measured {measured}% "
        f"({exact}% exact)"
    )


if __name__ == "__main__":
    main()
