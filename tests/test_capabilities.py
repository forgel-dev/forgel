from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel import capabilities
from forgel.capabilities import Capability
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.program_manifest import set_entries
from forgel.projects import create_project

REPO_ROOT = Path(__file__).resolve().parents[1]


class CapabilityTest(unittest.TestCase):
    def test_the_ios_simulator_needs_macos(self) -> None:
        with patch("forgel.capabilities.sys.platform", "linux"):
            capability = capabilities._ios()
        self.assertFalse(capability.available)
        self.assertIn("macOS", capability.detail)
        self.assertIn("Mac", capability.how_to)

    def test_a_missing_android_emulator_is_reported_with_instructions(
        self,
    ) -> None:
        with patch(
            "forgel.capabilities._android_emulator", return_value=None
        ), patch("forgel.capabilities.shutil.which", return_value=None):
            capability = capabilities._android()
        self.assertFalse(capability.available)
        self.assertIn("AVD", capability.how_to)

    def test_a_mobile_simulator_accepts_either_platform(self) -> None:
        ios = Capability("ios-simulator", True, "ios ok", "")
        android = Capability("android-emulator", False, "no android", "x")
        with patch(
            "forgel.capabilities._ios", return_value=ios
        ), patch(
            "forgel.capabilities._android", return_value=android
        ):
            capability = capabilities._mobile_simulator()
        self.assertTrue(capability.available)

    def test_docker_without_a_daemon_is_unavailable(self) -> None:
        with patch(
            "forgel.capabilities.shutil.which", return_value=None
        ):
            capability = capabilities._docker()
        self.assertFalse(capability.available)
        self.assertIn("Docker", capability.how_to)

    def test_message_explains_how_to_enable_the_tool(self) -> None:
        text = capabilities.message(
            [
                Capability(
                    "ios-simulator",
                    False,
                    "no simulator",
                    "install Xcode",
                )
            ]
        )
        self.assertIn("e2e skipped", text)
        self.assertIn("install Xcode", text)


class CapabilityRequirementTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        settings = Settings(
            home=Path(self._tmp.name),
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )
        ledger = Ledger(settings.db_path)
        self.addCleanup(ledger.close)
        project_id = create_project(
            settings,
            ledger,
            "Mobile demo",
            "A demo project.",
            mode="brownfield",
        )
        project = ledger.get_project(project_id)
        assert project is not None
        self.layout = ProjectLayout.detect(project["workspace"])

    def _role(self, role: str) -> None:
        set_entries(
            self.layout,
            [
                {
                    "id": "main",
                    "role": role,
                    "provider": "local",
                    "url": "",
                    "depends_on": [],
                }
            ],
        )

    def test_a_mobile_role_infers_the_simulator_requirement(self) -> None:
        self._role("mobile")
        self.assertEqual(
            capabilities.required(None, self.layout),
            ["mobile-simulator"],
        )

    def test_an_explicit_requirement_wins(self) -> None:
        self._role("mobile")
        from forgel.environment import Environment

        environment = Environment(
            e2e_requires=("ios-simulator",)
        )
        self.assertEqual(
            capabilities.required(environment, self.layout),
            ["ios-simulator"],
        )

    def test_unavailable_lists_the_missing_tool(self) -> None:
        self._role("ios")
        missing = Capability(
            "ios-simulator", False, "no simulator", "install Xcode"
        )
        with patch(
            "forgel.capabilities.check", return_value=missing
        ):
            self.assertEqual(
                capabilities.unavailable(None, self.layout), [missing]
            )


if __name__ == "__main__":
    unittest.main()
