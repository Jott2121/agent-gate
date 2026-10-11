"""Tests for scripts/scan_blocked_terms.py, the employer-term guard.

Every planted term is synthetic and lives only in a temp directory, so no real
blocked term is ever written to the repo.
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "scan_blocked_terms.py"
REPO_HASHES = ROOT / ".github" / "blocked-terms.sha256"

PLANTED_WORD = "zephyrquill"
PLANTED_PHRASE = "amber lattice"


def _digest(term):
    return hashlib.sha256(term.encode("utf-8")).hexdigest()


def _run(cwd, *args, markers=None):
    env = {k: v for k, v in os.environ.items() if k != "EMPLOYER_MARKERS"}
    if markers is not None:
        env["EMPLOYER_MARKERS"] = markers
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


class ScanTempRepoTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        self.hashes = self.repo / "terms.sha256"
        self.hashes.write_text(
            f"# synthetic\n{_digest(PLANTED_WORD)}\n{_digest(PLANTED_PHRASE)}\n"
        )
        self._write("README.md", "A clean tree about agent gates.\n")
        self._write(".cursor/rules/x.mdc", "policy text\n")
        self._write("results/run1.json", '{"note": "amber and lattice apart"}\n')

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        subprocess.run(["git", "add", "-f", rel], cwd=self.repo, check=True)

    def _scan(self, *args, markers=None):
        return _run(self.repo, "--hashes", str(self.hashes), *args, markers=markers)

    def test_clean_tree_passes(self):
        proc = self._scan()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("clean", proc.stdout)

    def test_planted_word_is_caught_without_echoing_it(self):
        self._write("docs/notes.md", "line one\nSee ZephyrQuill for details.\n")
        proc = self._scan()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("docs/notes.md:2: blocked term", proc.stdout)
        self.assertNotIn(PLANTED_WORD, (proc.stdout + proc.stderr).lower())

    def test_planted_two_word_phrase_is_caught_across_punctuation(self):
        self._write("results/run2.csv", "id,label\n7,Amber-LATTICE\n")
        proc = self._scan()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("results/run2.csv:2: blocked term", proc.stdout)

    def test_substrings_of_longer_words_are_not_hits(self):
        self._write("notes.txt", "zephyrquills and prezephyrquill are different words\n")
        self.assertEqual(self._scan().returncode, 0)

    def test_data_and_policy_folders_are_scanned_and_generated_dirs_are_not(self):
        for rel in ("fixtures/data.txt", "AGENTS.md", ".cursor/BUGBOT.md", ".github/workflows/ci.yml"):
            with self.subTest(path=rel):
                self._write(rel, f"{PLANTED_WORD}\n")
                proc = self._scan()
                self.assertEqual(proc.returncode, 1)
                self.assertIn(f"{rel}:1: blocked term", proc.stdout)
                subprocess.run(["git", "rm", "-q", "-f", rel], cwd=self.repo, check=True)
        self._write("node_modules/pkg/index.js", f"// {PLANTED_WORD}\n")
        self._write("build/out.txt", f"{PLANTED_WORD}\n")
        self.assertEqual(self._scan().returncode, 0)

    def test_employer_markers_regex_is_caught_even_when_not_in_hash_file(self):
        self._write("a.txt", "the Cobalt Heron project\n")
        self.assertEqual(self._scan().returncode, 0)
        proc = self._scan(markers=r"cobalt\s+heron|\bcbh\b")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("a.txt:1: blocked term (EMPLOYER_MARKERS)", proc.stdout)
        self.assertNotIn("heron", (proc.stdout + proc.stderr).lower())

    def test_hash_list_still_catches_planted_term_when_markers_unset_or_blank(self):
        self._write("a.txt", f"{PLANTED_WORD}\n")
        self.assertEqual(self._scan().returncode, 1)
        self.assertEqual(self._scan(markers="  ").returncode, 1)
        self.assertEqual(self._scan(markers="cobalt heron").returncode, 1)

    def test_invalid_employer_markers_fail_closed(self):
        for bad in ("cobalt(heron", "cobalt|"):
            with self.subTest(markers=bad):
                self.assertEqual(self._scan(markers=bad).returncode, 2)

    def test_hash_file_itself_is_not_scanned(self):
        # A markers regex that matches hex digests would otherwise flag it.
        self._write("terms.sha256", self.hashes.read_text())
        self.assertEqual(self._scan(markers=r"[0-9a-f]{64}").returncode, 0)

    def test_explicit_path_mode_scans_only_given_files(self):
        self._write("bad.txt", f"{PLANTED_WORD}\n")
        self.assertEqual(self._scan("README.md").returncode, 0)
        self.assertEqual(self._scan("bad.txt").returncode, 1)

    def test_binary_files_are_skipped(self):
        path = self.repo / "img.bin"
        path.write_bytes(b"\x00\x01" + PLANTED_WORD.encode() + b"\x00")
        subprocess.run(["git", "add", "img.bin"], cwd=self.repo, check=True)
        self.assertEqual(self._scan().returncode, 0)

    def test_missing_hash_file_fails_closed(self):
        self.hashes.unlink()
        proc = self._scan()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("cannot read hash file", proc.stderr)

    def test_empty_hash_file_fails_closed_even_with_markers_set(self):
        self.hashes.write_text("# comments only\n\n")
        proc = self._scan(markers="cobalt heron")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no digests", proc.stderr)

    def test_plain_text_line_in_hash_file_fails_closed(self):
        self.hashes.write_text(f"{_digest(PLANTED_WORD)}\n{PLANTED_PHRASE}\n")
        proc = self._scan()
        self.assertEqual(proc.returncode, 2)
        self.assertIn(":2: not a lowercase SHA-256 hex digest", proc.stderr)


class RepoTreeTests(unittest.TestCase):
    def test_committed_hash_file_is_well_formed_and_non_empty(self):
        lines = [
            line.strip()
            for line in REPO_HASHES.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        self.assertGreater(len(lines), 0)
        for line in lines:
            self.assertRegex(line, r"^[0-9a-f]{64}$")

    def test_repo_tree_is_clean(self):
        proc = _run(ROOT)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
