"""Tests for the ship-gate — Fleet Mode encoded as an enforceable checklist.

A gate is a named set of checks an agent must satisfy before it may claim 'done'.
Evaluation is FAIL-CLOSED: a check that isn't explicitly satisfied counts as
blocking. This is the discipline of 'deterministic checks, then an independent
refute-first review, then an honest receipt' — turned into something a tool can enforce.
"""
import unittest

from agent_gate import gate as G


class GateTests(unittest.TestCase):
    def test_default_ship_gate_encodes_fleet_mode_checks(self):
        ids = {c["id"] for c in G.DEFAULT_SHIP_GATE.checks}
        self.assertIn("deterministic_checks_pass", ids)
        self.assertIn("independent_refute_review", ids)
        self.assertIn("human_gated_if_irreversible", ids)
        self.assertIn("honest_receipt_logged", ids)

    def test_passes_when_all_checks_satisfied(self):
        ev = {c["id"]: True for c in G.DEFAULT_SHIP_GATE.checks}
        res = G.DEFAULT_SHIP_GATE.evaluate(ev)
        self.assertTrue(res.passed)
        self.assertEqual(res.blocking, [])

    def test_a_false_check_blocks(self):
        ev = {c["id"]: True for c in G.DEFAULT_SHIP_GATE.checks}
        ev["independent_refute_review"] = False
        res = G.DEFAULT_SHIP_GATE.evaluate(ev)
        self.assertFalse(res.passed)
        self.assertIn("independent_refute_review", res.blocking)

    def test_missing_check_is_fail_closed(self):
        ev = {c["id"]: True for c in G.DEFAULT_SHIP_GATE.checks}
        del ev["no_secrets"]
        res = G.DEFAULT_SHIP_GATE.evaluate(ev)
        self.assertFalse(res.passed)
        self.assertIn("no_secrets", res.blocking)

    def test_extra_evidence_keys_are_ignored(self):
        ev = {c["id"]: True for c in G.DEFAULT_SHIP_GATE.checks}
        ev["irrelevant"] = False
        self.assertTrue(G.DEFAULT_SHIP_GATE.evaluate(ev).passed)

    def test_custom_gate_evaluates_its_own_checks(self):
        g = G.Gate("mini", [{"id": "a", "description": "x"}, {"id": "b", "description": "y"}])
        self.assertFalse(g.evaluate({"a": True}).passed)              # b missing -> blocked
        self.assertTrue(g.evaluate({"a": True, "b": True}).passed)

    def test_non_true_values_do_not_pass(self):
        g = G.Gate("mini", [{"id": "a", "description": "x"}])
        self.assertFalse(g.evaluate({"a": "yes"}).passed)            # only literal True passes
        self.assertFalse(g.evaluate({"a": 1}).passed)


if __name__ == "__main__":
    unittest.main()
