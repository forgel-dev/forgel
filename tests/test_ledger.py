from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.ledger import Ledger, new_project_id


class LedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ledger = Ledger(Path(self._tmp.name) / "ledger.sqlite3")
        self.addCleanup(self.ledger.close)
        self.project_id = new_project_id("Demo Project")
        self.workspace = Path(self._tmp.name) / "workspace"
        self.ledger.create_project(
            self.project_id, "Demo Project", "A demo brief.", str(self.workspace)
        )

    def test_create_and_get_project(self) -> None:
        project = self.ledger.get_project(self.project_id)
        self.assertIsNotNone(project)
        assert project is not None
        self.assertEqual(project["name"], "Demo Project")
        self.assertEqual(project["brief"], "A demo brief.")
        self.assertIsNone(project["recipe_id"])

    def test_project_id_has_slug_prefix(self) -> None:
        self.assertTrue(self.project_id.startswith("demo-project-"))

    def test_event_idempotency(self) -> None:
        key = f"{self.project_id}:intake:completed"
        first = self.ledger.append_event(self.project_id, "intake", idempotency_key=key)
        second = self.ledger.append_event(self.project_id, "intake", idempotency_key=key)
        self.assertEqual(first["seq"], second["seq"])
        self.assertEqual(len(self.ledger.events(self.project_id)), 1)

    def test_completed_event_is_visible(self) -> None:
        self.assertFalse(self.ledger.has_completed(self.project_id, "intake"))
        self.ledger.append_event(self.project_id, "intake", status="completed")
        self.assertTrue(self.ledger.has_completed(self.project_id, "intake"))

    def test_failed_event_is_not_completed(self) -> None:
        self.ledger.append_event(
            self.project_id, "intake", status="failed", payload={"error": "boom"}
        )
        self.assertFalse(self.ledger.has_completed(self.project_id, "intake"))
        events = self.ledger.events(self.project_id)
        self.assertEqual(events[0]["status"], "failed")
        self.assertEqual(events[0]["attempt"], 1)

    def test_checkpoint(self) -> None:
        self.assertIsNone(self.ledger.checkpoint(self.project_id))
        self.ledger.set_checkpoint(self.project_id, "recipe")
        self.assertEqual(self.ledger.checkpoint(self.project_id), "recipe")
        self.ledger.set_checkpoint(self.project_id, "dev")
        self.assertEqual(self.ledger.checkpoint(self.project_id), "dev")

    def test_generation_starts_at_one(self) -> None:
        self.assertEqual(self.ledger.current_generation(self.project_id), 1)

    def test_generation_scopes_completed_stages(self) -> None:
        self.ledger.append_event(
            self.project_id, "review", status="completed", generation=1
        )
        generation = self.ledger.start_generation(self.project_id, "review")

        self.assertEqual(generation, 2)
        self.assertEqual(self.ledger.current_generation(self.project_id), 2)
        self.assertEqual(
            self.ledger.checkpoint_state(self.project_id), ("review", 2)
        )
        self.assertTrue(self.ledger.has_completed(self.project_id, "review", 1))
        self.assertFalse(self.ledger.has_completed(self.project_id, "review", 2))

        self.ledger.append_event(
            self.project_id, "review", status="completed", generation=2
        )
        self.assertTrue(self.ledger.has_completed(self.project_id, "review", 2))
        self.assertEqual(len(self.ledger.events(self.project_id)), 2)


if __name__ == "__main__":
    unittest.main()
