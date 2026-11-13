from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.approvals import (
    ApprovalError,
    is_approved,
    latest_approval,
    record_approval,
)
from forgel.ledger import Ledger, new_project_id

REPO_ROOT = Path(__file__).resolve().parents[1]


class ApprovalTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        self.ledger = Ledger(self.home / "ledger.sqlite3")
        self.addCleanup(self.ledger.close)
        self.project_id = new_project_id("Approval Demo")
        self.workspace = self.home / "workspace"
        self.workspace.mkdir()
        self.ledger.create_project(
            self.project_id,
            "Approval Demo",
            "A demo brief.",
            str(self.workspace),
        )

    def _at_gate(self) -> None:
        self.ledger.set_checkpoint(self.project_id, "approval")

    def test_staging_approval_writes_ledger_and_artifact(self) -> None:
        self._at_gate()
        record = record_approval(
            self.ledger,
            self.project_id,
            scope="staging",
            actor="@tester",
            notes="looks good",
        )

        self.assertEqual(record["decision"], "approved")
        self.assertEqual(record["generation"], 1)
        self.assertTrue(
            is_approved(self.ledger, self.project_id, "staging", 1)
        )

        artifact = (
            self.workspace / "docs" / "program" / "approvals.md"
        ).read_text(encoding="utf-8")
        self.assertIn("| staging | 1 | approved | @tester |", artifact)
        self.assertIn("looks good", artifact)

        events = self.ledger.events(self.project_id)
        approval_events = [event for event in events if event["stage"] == "approval"]
        self.assertEqual(len(approval_events), 1)
        self.assertEqual(approval_events[0]["status"], "approved")

    def test_repeated_approval_is_idempotent(self) -> None:
        self._at_gate()
        first = record_approval(
            self.ledger, self.project_id, scope="staging", actor="@tester"
        )
        second = record_approval(
            self.ledger, self.project_id, scope="staging", actor="@tester"
        )
        self.assertEqual(first["seq"], second["seq"])
        self.assertEqual(len(self.ledger.approvals(self.project_id)), 1)

    def test_production_requires_the_compliance_acknowledgement(self) -> None:
        self._at_gate()
        record_approval(
            self.ledger, self.project_id, scope="staging", actor="@tester"
        )
        self.ledger.set_checkpoint(self.project_id, "done")
        with self.assertRaises(ApprovalError):
            record_approval(
                self.ledger,
                self.project_id,
                scope="production",
                actor="@tester",
            )
        record = record_approval(
            self.ledger,
            self.project_id,
            scope="production",
            actor="@tester",
            compliance_ack=True,
        )
        self.assertEqual(record["scope"], "production")
        self.assertEqual(record["compliance_ack"], 1)

    def test_production_requires_staging_approval(self) -> None:
        self.ledger.set_checkpoint(self.project_id, "done")
        with self.assertRaises(ApprovalError):
            record_approval(
                self.ledger,
                self.project_id,
                scope="production",
                actor="@tester",
                compliance_ack=True,
            )

    def test_approvals_are_generation_scoped(self) -> None:
        self._at_gate()
        record_approval(
            self.ledger, self.project_id, scope="staging", actor="@tester"
        )
        self.ledger.start_generation(self.project_id, "review")
        self.assertFalse(
            is_approved(self.ledger, self.project_id, "staging", 2)
        )
        self.assertIsNone(
            latest_approval(self.ledger, self.project_id, "staging", 2)
        )
        self.assertTrue(
            is_approved(self.ledger, self.project_id, "staging", 1)
        )

    def test_staging_is_rejected_outside_the_gate(self) -> None:
        with self.assertRaises(ApprovalError):
            record_approval(
                self.ledger, self.project_id, scope="staging", actor="@tester"
            )

    def test_unknown_project_is_rejected(self) -> None:
        with self.assertRaises(ApprovalError):
            record_approval(
                self.ledger, "missing", scope="staging", actor="@tester"
            )


if __name__ == "__main__":
    unittest.main()
