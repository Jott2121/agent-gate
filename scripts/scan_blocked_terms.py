#!/usr/bin/env python3
"""Fail if any tracked file contains a blocked employer term.

The blocked terms are never stored in the repo. ``.github/blocked-terms.sha256``
holds one SHA-256 hex digest per term, computed over the lowercased term with
its words joined by single spaces. The scanner splits each line of text into
lowercase alphanumeric words, hashes every word and every pair of adjacent
words, and reports a hit when a digest matches. This base list is required:
the scan catches the listed terms with no secret configured.

Extra markers can be supplied through the ``EMPLOYER_MARKERS`` environment
variable (e.g. from an Actions secret of the same name): a regex alternation
matched case-insensitively against each line, in addition to the hash list.

Exit codes: 0 clean, 1 blocked term found, 2 configuration or read error.
A missing, empty, or malformed hash file, or an invalid ``EMPLOYER_MARKERS``
regex, is a configuration error, so the check fails closed. Hits are reported
as ``path:line`` plus a digest prefix or marker label; the matched text is
never printed.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HASH_FILE = ROOT / ".github" / "blocked-terms.sha256"
PHRASE_WORDS = 2
# Generated or vendored output only. Data folders (results/, fixtures, docs) and
# policy files (AGENTS.md, .cursor/, .github/) are scanned.
EXCLUDED_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "build",
        "dist",
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
    }
)
WORD = re.compile(r"[a-z0-9]+")
DIGEST = re.compile(r"[0-9a-f]{64}")


class ConfigError(Exception):
    pass


def normalize(term: str) -> str:
    return " ".join(WORD.findall(term.lower()))


def digest(term: str) -> str:
    return hashlib.sha256(normalize(term).encode("utf-8")).hexdigest()


def load_hashes(path: Path) -> set[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ConfigError(f"cannot read hash file {path}: {exc}") from exc
    hashes = set()
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not DIGEST.fullmatch(line):
            raise ConfigError(f"{path}:{number}: not a lowercase SHA-256 hex digest")
        hashes.add(line)
    if not hashes:
        raise ConfigError(f"hash file {path} has no digests")
    return hashes


def load_markers(value: str | None) -> re.Pattern[str] | None:
    """Compile ``EMPLOYER_MARKERS``; unset or blank means hash list only."""
    if not value or not value.strip():
        return None
    try:
        pattern = re.compile(value.strip(), re.IGNORECASE)
    except re.error as exc:
        raise ConfigError(f"EMPLOYER_MARKERS is not a valid regex: {exc}") from exc
    if pattern.search(""):
        raise ConfigError("EMPLOYER_MARKERS matches the empty string (stray '|'?)")
    return pattern


def is_excluded(path: str) -> bool:
    parts = Path(path).parts
    return any(p in EXCLUDED_DIRS or p.endswith(".egg-info") for p in parts)


def tracked_files(cwd: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"], cwd=cwd, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise ConfigError(f"git ls-files failed: {proc.stderr.strip()}")
    return [p for p in proc.stdout.split("\0") if p and not is_excluded(p)]


def scan_text(
    text: str, hashes: set[str], markers: re.Pattern[str] | None
) -> list[tuple[int, str]]:
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        words = WORD.findall(line.lower())
        for start in range(len(words)):
            for size in range(1, PHRASE_WORDS + 1):
                if start + size > len(words):
                    break
                h = hashlib.sha256(
                    " ".join(words[start : start + size]).encode("utf-8")
                ).hexdigest()
                if h in hashes:
                    hits.append((number, f"sha256 {h[:12]}"))
        if markers is not None and markers.search(line):
            hits.append((number, "EMPLOYER_MARKERS"))
    return hits


def scan_file(
    path: Path, hashes: set[str], markers: re.Pattern[str] | None
) -> list[tuple[int, str]]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    if b"\0" in data[:8192]:
        return []
    return scan_text(data.decode("utf-8", errors="replace"), hashes, markers)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "paths",
        nargs="*",
        help="files to scan (default: every tracked file under the current directory)",
    )
    parser.add_argument("--hashes", type=Path, default=DEFAULT_HASH_FILE)
    args = parser.parse_args(argv)

    try:
        hashes = load_hashes(args.hashes)
        markers = load_markers(os.environ.get("EMPLOYER_MARKERS"))
        cwd = Path.cwd()
        hash_file = args.hashes.resolve()
        paths = [
            p
            for p in (args.paths or tracked_files(cwd))
            if (cwd / p).resolve() != hash_file
        ]
        hits = []
        for p in paths:
            for number, label in scan_file(cwd / p, hashes, markers):
                hits.append(f"{p}:{number}: blocked term ({label})")
    except ConfigError as exc:
        print(f"scan_blocked_terms: {exc}", file=sys.stderr)
        return 2

    if hits:
        print("\n".join(hits))
        print(f"scan_blocked_terms: {len(hits)} blocked term hit(s)", file=sys.stderr)
        return 1
    extra = " + EMPLOYER_MARKERS" if markers else ""
    print(f"scan_blocked_terms: clean ({len(paths)} files, {len(hashes)} hashed terms{extra})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
