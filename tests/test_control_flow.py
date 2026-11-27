from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel import control_flow, controller, runtime_ops, tasks
from forgel.artifacts import write_json
from forgel.control_flow import CHAT, CONTROLLER, RUNTIME, control_state
from forgel.layout import ProjectLayout
from forgel.runtime_model import process_model


class ControlFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.layout = ProjectLayout.detect(Path(self._tmp.name))

    def _task(self, status: str) -> dict:
        task = tasks.create_task(
            self.layout,
            "Control flow",
            ["The requested result is delivered"],
            ["The result is verified"],
            repo_id="main",
        )
        return tasks.update_task(self.layout, str(task["id"]), status=status)

    def _release(self, status: str) -> None:
        write_json(
            self.layout.artifact("docs/program/releases/r1/release.json"),
            {"id": "r1", "title": "Release", "status": status, "repos": {}},
        )

    def test_idle_work_is_led_by_chat(self) -> None:
        state = control_state(self.layout)
        self.assertEqual(state.leader, CHAT)
        self.assertTrue(any("planner" in branch for branch in state.branches))
        self.assertTrue(any("controller" in branch for branch in state.branches))

    def test_running_work_is_led_by_runtime(self) -> None:
        self._task("running")
        state = control_state(self.layout)
        self.assertEqual(state.leader, RUNTIME)
        self.assertIn("controller takes over", state.handoff)

    def test_stopped_task_is_led_by_controller(self) -> None:
        self._task("failed")
        state = control_state(self.layout)
        self.assertEqual(state.leader, CONTROLLER)
        self.assertIn("recovery", state.detail)
        self.assertNotIn("chat chooses", state.handoff)

    def test_stopped_release_is_led_by_controller(self) -> None:
        self._release("blocked")
        state = control_state(self.layout)
        self.assertEqual(state.leader, CONTROLLER)
        self.assertIn("release r1", state.detail)

    def test_active_release_is_led_by_runtime(self) -> None:
        self._release("running")
        state = control_state(self.layout)
        self.assertEqual(state.leader, RUNTIME)
        self.assertIn("release train", state.detail)

    def test_operation_names_have_one_source(self) -> None:
        self.assertEqual(runtime_ops.OPERATIONS, control_flow.RUNTIME_OPERATIONS)
        self.assertEqual(
            controller.OPERATIONS, control_flow.CONTROLLER_OPERATIONS
        )
        self.assertEqual(len(runtime_ops.OPERATIONS), len(set(runtime_ops.OPERATIONS)))
        self.assertEqual(len(controller.OPERATIONS), len(set(controller.OPERATIONS)))

    def test_main_chat_receives_the_current_owner_and_branches(self) -> None:
        self._task("failed")
        text = process_model(self.layout, {"id": "demo"})
        self.assertIn("Control ownership and visibility:", text)
        self.assertIn("Current control owner: controller", text)
        self.assertIn("Available branches:", text)
        self.assertIn("controller chooses a valid recovery operation", text)


if __name__ == "__main__":
    unittest.main()
