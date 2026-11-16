"""Cost aggregation, acceptance records and the cost report."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from forgel import entry
from forgel.agent import ProjectAgent
from forgel.config import Settings
from forgel.console import run_console
from forgel.costs import cost_command, cost_report
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.projects import create_project
from forgel.task_review import accept_task, reject_task
from forgel.tasks import create_task

REPO_ROOT = Path(__file__).resolve().parents[1]

ENVELOPE = json.dumps(
    {
        "kind": "answer",
        "reply": "The demo project is quiet; nothing is running right now.",
    }
)


def _feed(lines: list[str]):
    remaining = list(lines)

    def read(_prompt: str) -> str:
        if not remaining:
            raise EOFError
        return remaining.pop(0)

    return read


def _total_from_report(text: str) -> float:
    for line in text.splitlines():
        if line.startswith("Total cost: "):
            return float(line.split("Total cost: ", 1)[1].lstrip("$"))
    raise AssertionError(f"no total cost line in:\n{text}")


def _home(name: str) -> tuple[tempfile.TemporaryDirectory, Path]:
    handle = tempfile.TemporaryDirectory()
    return handle, Path(handle.name)


class CostReportTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        self.settings = Settings(
            home=self.home,
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)
        self.project_id = create_project(
            self.settings, self.ledger, "Cost demo", "A demo brief."
        )
        self.project = self.ledger.get_project(self.project_id)
        assert self.project is not None
        self.layout = ProjectLayout.detect(self.project["workspace"])

    def _event(
        self, stage: str, cost: float, generation: int = 1
    ) -> None:
        self.ledger.append_event(
            self.project_id,
            stage,
            status="completed",
            cost=cost,
            idempotency_key=f"{self.project_id}:g{generation}:{stage}:{cost}",
            generation=generation,
        )

    def _task(self, title: str = "Do it") -> dict:
        return create_task(self.layout, title, ["Do it"], ["It is done"])

    def test_cost_summary_aggregates_recorded_events(self) -> None:
        self._event("intake", 0.5)
        self._event("recipe", 0.25)
        self._event("review", 1.25, generation=2)
        summary = self.ledger.cost_summary(self.project_id)
        self.assertAlmostEqual(summary["total"], 2.0)
        self.assertAlmostEqual(summary["by_stage"]["intake"], 0.5)
        self.assertAlmostEqual(summary["by_stage"]["recipe"], 0.25)
        self.assertAlmostEqual(summary["by_stage"]["review"], 1.25)
        self.assertAlmostEqual(summary["by_generation"][1], 0.75)
        self.assertAlmostEqual(summary["by_generation"][2], 1.25)

    def test_cost_summary_of_an_empty_project_is_zero(self) -> None:
        summary = self.ledger.cost_summary(self.project_id)
        self.assertEqual(summary["total"], 0.0)
        self.assertEqual(summary["by_stage"], {})

    def test_report_total_equals_the_sum_of_event_costs(self) -> None:
        self._event("intake", 0.5)
        self._event("recipe", 0.25)
        self._event("review", 1.25, generation=2)
        recorded = sum(
            float(event["cost"])
            for event in self.ledger.events(self.project_id)
        )
        text = cost_report(self.ledger, self.project_id)
        self.assertAlmostEqual(_total_from_report(text), recorded)
        self.assertIn("Cost per stage:", text)
        self.assertIn("review", text)
        self.assertIn("Acceptance count: 0", text)

    def test_cli_prints_the_ledger_totals(self) -> None:
        self._event("intake", 1.5)
        self._event("review", 2.0)
        recorded = sum(
            float(event["cost"])
            for event in self.ledger.events(self.project_id)
        )
        buffer = StringIO()
        with redirect_stdout(buffer):
            code = cost_command([self.project_id, "--home", str(self.home)])
        self.assertEqual(code, 0)
        text = buffer.getvalue()
        self.assertAlmostEqual(_total_from_report(text), recorded)
        self.assertIn("Acceptance count: 0", text)

    def test_accepting_a_task_records_an_acceptance(self) -> None:
        task = self._task()
        accept_task(
            self.settings,
            self.ledger,
            self.project,
            task,
            actor="owner",
            notes="the patch does what the task asked",
        )
        acceptances = self.ledger.acceptances(self.project_id)
        self.assertEqual(len(acceptances), 1)
        record = acceptances[0]
        self.assertEqual(record["task_id"], task["id"])
        self.assertEqual(record["decision"], "accepted")
        self.assertEqual(record["actor"], "owner")
        self.assertEqual(
            record["reason"], "the patch does what the task asked"
        )

    def test_rejecting_a_task_records_the_reason(self) -> None:
        task = self._task("Fix the header")
        reject_task(
            self.settings,
            self.ledger,
            self.project,
            task,
            actor="reviewer",
            notes="the header is unchanged",
        )
        acceptances = self.ledger.acceptances(self.project_id)
        self.assertEqual(len(acceptances), 1)
        self.assertEqual(acceptances[0]["decision"], "rejected")
        self.assertEqual(acceptances[0]["actor"], "reviewer")
        self.assertEqual(
            acceptances[0]["reason"], "the header is unchanged"
        )
        text = cost_report(self.ledger, self.project_id)
        self.assertIn("Acceptance count: 1 (accepted 0, rejected 1)", text)
        self.assertIn("the header is unchanged", text)

    def test_the_console_reports_cost_on_a_scripted_home(self) -> None:
        self._event("intake", 0.75)
        task = self._task()
        accept_task(
            self.settings,
            self.ledger,
            self.project,
            task,
            actor="owner",
            notes="accepted after review",
        )
        output: list[str] = []
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient([ENVELOPE]),
        )
        run_console(
            self.settings,
            self.ledger,
            project_id=self.project_id,
            daemon=False,
            input_fn=_feed(["/cost", "/quit"]),
            output=output.append,
            agent=agent,
        )
        text = "\n".join(output)
        self.assertIn("Cost report for", text)
        self.assertIn("Total cost: $0.75", text)
        self.assertIn("Acceptance count: 1 (accepted 1, rejected 0)", text)
        self.assertIn("accepted after review", text)


class CostEntryPointTest(unittest.TestCase):
    def test_the_entry_point_routes_cost_to_the_ledger_report(self) -> None:
        handle, home = _home("cost-entry")
        self.addCleanup(handle.cleanup)
        settings = Settings(
            home=home,
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )
        ledger = Ledger(settings.db_path)
        try:
            project_id = create_project(
                settings, ledger, "Entry demo", "A brief."
            )
            ledger.append_event(
                project_id, "intake", cost=1.25, idempotency_key="entry:intake"
            )
            recorded = sum(
                float(event["cost"])
                for event in ledger.events(project_id)
            )
        finally:
            ledger.close()
        buffer = StringIO()
        with redirect_stdout(buffer):
            code = entry.main(["cost", project_id, "--home", str(home)])
        self.assertEqual(code, 0)
        text = buffer.getvalue()
        self.assertAlmostEqual(_total_from_report(text), recorded)
        self.assertIn("Cost per stage:", text)


class LegacyLedgerTest(unittest.TestCase):
    def _make_legacy(self, path: Path) -> None:
        conn = sqlite3.connect(path)
        conn.executescript(
            """
            CREATE TABLE projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                brief TEXT NOT NULL,
                recipe_id TEXT,
                workspace TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'completed',
                attempt INTEGER NOT NULL DEFAULT 1,
                idempotency_key TEXT NOT NULL UNIQUE,
                artifact_refs TEXT NOT NULL DEFAULT '[]',
                cost REAL NOT NULL DEFAULT 0,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE TABLE approvals (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                scope TEXT NOT NULL,
                decision TEXT NOT NULL,
                actor TEXT NOT NULL,
                compliance_ack INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                release_sha TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO projects VALUES "
            "('p1', 'Legacy', 'brief', NULL, '/tmp', 'now')"
        )
        conn.execute(
            "INSERT INTO events (project_id, stage, idempotency_key, cost, "
            "created_at) VALUES ('p1', 'agent', 'e1', 1.5, 'now')"
        )
        conn.execute(
            "INSERT INTO approvals (project_id, scope, decision, actor, "
            "notes, created_at) VALUES "
            "('p1', 'task:t1', 'accepted', 'owner', 'ok', 'now')"
        )
        conn.commit()
        conn.close()

    def test_cost_report_reads_a_legacy_ledger_without_migrating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.sqlite3"
            self._make_legacy(path)
            ledger = Ledger(path, read_only=True)
            self.assertFalse(ledger._has_column("events", "generation"))
            self.assertEqual(
                ledger.cost_summary("p1")["total"], 1.5
            )
            self.assertEqual(
                ledger.cost_summary("p1")["by_generation"], {1: 1.5}
            )
            decisions = ledger.acceptances("p1")
            self.assertEqual(len(decisions), 1)
            self.assertEqual(decisions[0]["task_id"], "t1")
            ledger.close()
            check = sqlite3.connect(path)
            columns = {
                row[1]
                for row in check.execute("PRAGMA table_info(events)")
            }
            check.close()
            self.assertNotIn("generation", columns)

    def test_cost_command_reads_a_legacy_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            path = home / "ledger.sqlite3"
            self._make_legacy(path)
            buffer = StringIO()
            with redirect_stdout(buffer):
                code = entry.main(["cost", "p1", "--home", str(home)])
            self.assertEqual(code, 0)
            self.assertAlmostEqual(_total_from_report(buffer.getvalue()), 1.5)

    def test_normal_ledger_migrates_a_legacy_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.sqlite3"
            self._make_legacy(path)
            ledger = Ledger(path)
            self.assertTrue(ledger._has_column("events", "generation"))
            self.assertEqual(
                ledger.cost_summary("p1")["total"], 1.5
            )
            ledger.close()


if __name__ == "__main__":
    unittest.main()
