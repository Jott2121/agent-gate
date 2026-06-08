"""Tests for the append-only, hash-chained receipts ledger.

Every gate decision is recorded as an honest receipt (decision, metric, value,
verdict) linked into a sha256 hash chain — so the log is tamper-evident: you can
prove no receipt was edited or removed after the fact. "Receipts over hype,"
enforced by the data structure.
"""
import json
import unittest

from agent_gate import ledger as L


class LedgerTests(unittest.TestCase):
    def setUp(self):
        # deterministic clock so hashes are reproducible in tests
        self._t = iter(f"2026-01-01T00:00:0{i}Z" for i in range(9))
        self.led = L.Ledger(":memory:", clock=lambda: next(self._t))

    def test_append_returns_sequenced_hashed_entry(self):
        e = self.led.append(decision="adopt X", metric="tests", value=101, verdict="kept")
        self.assertEqual(e["seq"], 1)
        self.assertEqual(e["verdict"], "kept")
        self.assertEqual(e["prev_hash"], L.GENESIS)
        self.assertTrue(e["hash"])

    def test_chain_links_each_entry_to_the_prior(self):
        a = self.led.append(decision="a", metric="m", value=1, verdict="kept")
        b = self.led.append(decision="b", metric="m", value=2, verdict="killed")
        self.assertEqual(b["prev_hash"], a["hash"])
        self.assertEqual(b["seq"], 2)

    def test_verify_chain_true_when_intact(self):
        self.led.append(decision="a", metric="m", value=1, verdict="kept")
        self.led.append(decision="b", metric="m", value=2, verdict="kept")
        self.assertTrue(self.led.verify_chain())

    def test_verify_chain_false_when_a_receipt_is_tampered(self):
        self.led.append(decision="a", metric="m", value=1, verdict="kept")
        self.led.append(decision="b", metric="m", value=2, verdict="kept")
        self.led._entries[0]["value"] = 999  # tamper after the fact
        self.assertFalse(self.led.verify_chain())

    def test_read_all_returns_entries_in_order(self):
        self.led.append(decision="a", metric="m", value=1, verdict="kept")
        self.led.append(decision="b", metric="m", value=2, verdict="kept")
        rows = self.led.read_all()
        self.assertEqual([r["decision"] for r in rows], ["a", "b"])

    def test_persists_to_jsonl_file(self):
        import tempfile, os
        p = os.path.join(tempfile.mkdtemp(), "receipts.jsonl")
        t = iter(f"2026-01-01T00:00:0{i}Z" for i in range(9))
        led = L.Ledger(p, clock=lambda: next(t))
        led.append(decision="a", metric="m", value=1, verdict="kept")
        # a fresh ledger over the same file sees the persisted, valid chain
        led2 = L.Ledger(p)
        self.assertEqual(len(led2.read_all()), 1)
        self.assertTrue(led2.verify_chain())
        with open(p) as f:
            self.assertEqual(json.loads(f.readline())["decision"], "a")


if __name__ == "__main__":
    unittest.main()
