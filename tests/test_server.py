"""Behavior tests for the MCP tool layer.

Skipped automatically if the `mcp` SDK isn't installed (e.g. local dev on a
Python the SDK doesn't support yet); CI installs `mcp` so these run there. The
`@mcp.tool()` decorator returns the underlying function, so we can call the tools
directly and assert real behavior — not just that the module imports.
"""
import os
import tempfile
import unittest


def _server_or_skip():
    try:
        from agent_gate import server
        return server
    except ImportError as e:  # mcp SDK not present
        raise unittest.SkipTest(f"mcp SDK not installed: {e}")


class ServerToolTests(unittest.TestCase):
    def setUp(self):
        self.server = _server_or_skip()
        os.environ["AGENT_GATE_LEDGER"] = os.path.join(tempfile.mkdtemp(), "receipts.jsonl")

    def tearDown(self):
        os.environ.pop("AGENT_GATE_LEDGER", None)

    def test_server_is_named_agent_gate(self):
        self.assertEqual(self.server.mcp.name, "agent-gate")

    def test_gate_checklist_returns_the_ship_checks(self):
        out = self.server.gate_checklist()
        ids = {c["id"] for c in out["checks"]}
        self.assertIn("independent_refute_review", ids)

    def test_verify_gate_is_fail_closed(self):
        all_true = {c["id"]: True for c in self.server.gate_checklist()["checks"]}
        self.assertTrue(self.server.verify_gate(all_true)["passed"])
        missing = dict(all_true); missing.pop("no_secrets")
        res = self.server.verify_gate(missing)
        self.assertFalse(res["passed"])
        self.assertIn("no_secrets", res["blocking"])

    def test_record_and_read_receipts_roundtrip_with_intact_chain(self):
        self.server.record_receipt(decision="ship feature", metric="tests", value="13", verdict="shipped")
        out = self.server.read_receipts()
        self.assertEqual(len(out["receipts"]), 1)
        self.assertTrue(out["chain_intact"])


if __name__ == "__main__":
    unittest.main()
