from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.presets import (
    PresetError,
    find_preset,
    load_presets,
    read_versions,
    tag_ref_paths,
    update_tag_refs,
    write_version,
)
from forgel.program_manifest import entries, set_entries, write_program
from forgel.projects import create_project

REPO_ROOT = Path(__file__).resolve().parents[1]


class PresetTest(unittest.TestCase):
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
        self.presets = load_presets(self.settings.registry_path)
        self.repo = self.home / "repo"
        self.repo.mkdir()

    def test_python_reads_and_writes_pyproject_and_package_version(
        self,
    ) -> None:
        write_text(
            self.repo / "pyproject.toml",
            '[project]\nname = "demo"\nversion = "0.1.0"\n',
        )
        write_text(
            self.repo / "src" / "demo" / "__init__.py",
            '__version__ = "0.1.0"\n',
        )
        preset = find_preset(self.presets, self.repo, {})
        assert preset is not None
        self.assertEqual(preset.id, "python")
        sources = read_versions(self.presets, self.repo, {})
        self.assertIn(("0.1.0", "preset python pyproject.toml"), sources)
        self.assertIn(
            ("0.1.0", "preset python src/demo/__init__.py"), sources
        )

        preset_id, changed = write_version(
            self.presets, self.repo, {}, "0.2.0"
        )

        self.assertEqual(preset_id, "python")
        self.assertIn("pyproject.toml", changed)
        self.assertIn("src/demo/__init__.py", changed)
        self.assertIn(
            'version = "0.2.0"',
            (self.repo / "pyproject.toml").read_text(encoding="utf-8"),
        )
        self.assertIn(
            '__version__ = "0.2.0"',
            (self.repo / "src" / "demo" / "__init__.py").read_text(
                encoding="utf-8"
            ),
        )

    def test_python_dynamic_version_uses_the_package_constant(self) -> None:
        write_text(
            self.repo / "pyproject.toml",
            '[project]\nname = "demo"\ndynamic = ["version"]\n',
        )
        write_text(
            self.repo / "demo" / "__init__.py",
            '__version__ = "0.1.0"\n',
        )

        preset_id, changed = write_version(
            self.presets, self.repo, {}, "0.2.0"
        )

        self.assertEqual(preset_id, "python")
        self.assertEqual(changed, ["demo/__init__.py"])
        pyproject = (self.repo / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        self.assertIn('dynamic = ["version"]', pyproject)
        self.assertNotIn('version = "0.2.0"', pyproject)

    def test_node_bumps_the_root_and_app_manifests(self) -> None:
        for path, version in (
            ("package.json", "1.2.3"),
            ("apps/web/package.json", "1.0.0"),
            ("apps/mobile/package.json", "1.0.0"),
        ):
            write_text(
                self.repo / path,
                json.dumps({"name": path, "version": version}) + "\n",
            )
        preset = find_preset(self.presets, self.repo, {})
        assert preset is not None
        self.assertEqual(preset.id, "node")

        preset_id, changed = write_version(
            self.presets, self.repo, {}, "1.3.0"
        )

        self.assertEqual(preset_id, "node")
        self.assertEqual(
            changed,
            [
                "apps/mobile/package.json",
                "apps/web/package.json",
                "package.json",
            ],
        )
        for path in (
            "package.json",
            "apps/web/package.json",
            "apps/mobile/package.json",
        ):
            data = json.loads(
                (self.repo / path).read_text(encoding="utf-8")
            )
            self.assertEqual(data["version"], "1.3.0")

    def test_rails_writes_only_the_named_constant(self) -> None:
        write_text(
            self.repo / "Gemfile",
            'source "https://rubygems.org"\n',
        )
        write_text(
            self.repo / "config" / "initializers" / "version.rb",
            'API_VERSION = "1.8.5"\nASSETS_VERSION = "1.8.3"\n',
        )
        preset = find_preset(self.presets, self.repo, {})
        assert preset is not None
        self.assertEqual(preset.id, "rails")

        preset_id, changed = write_version(
            self.presets, self.repo, {}, "1.9.0"
        )

        self.assertEqual(preset_id, "rails")
        self.assertEqual(
            changed, ["config/initializers/version.rb"]
        )
        text = (
            self.repo / "config" / "initializers" / "version.rb"
        ).read_text(encoding="utf-8")
        self.assertIn('API_VERSION = "1.9.0"', text)
        self.assertIn('ASSETS_VERSION = "1.8.3"', text)

    def test_an_explicit_preset_wins_over_detection(self) -> None:
        write_text(self.repo / "pyproject.toml", "[project]\n")
        write_text(self.repo / "package.json", '{"version": "1.0.0"}\n')

        preset = find_preset(self.presets, self.repo, {})
        assert preset is not None
        self.assertEqual(preset.id, "python")
        chosen = find_preset(self.presets, self.repo, {"preset": "node"})
        assert chosen is not None
        self.assertEqual(chosen.id, "node")

    def test_release_tag_refs_move_to_the_new_version(self) -> None:
        write_text(self.repo / "pyproject.toml", "[project]\n")
        write_text(
            self.repo / "install.sh",
            'TAG=${FORGEL_CODE_TAG:-v0.1.0}\n',
        )
        write_text(
            self.repo / "README.md",
            "curl -fsSL https://example/v0.1.0/install.sh | sh\n",
        )
        write_text(
            self.repo / "CHANGELOG.md",
            "## [0.1.0] - 2026-01-01\n",
        )

        paths = tag_ref_paths(
            self.presets, self.repo, {}, "0.1.0", "0.1.1"
        )

        self.assertEqual(paths, ["README.md", "install.sh"])
        preset_id, changed = update_tag_refs(
            self.presets, self.repo, {}, "0.1.0", "0.1.1"
        )
        self.assertEqual(preset_id, "python")
        self.assertEqual(changed, ["README.md", "install.sh"])
        self.assertIn(
            "v0.1.1",
            (self.repo / "install.sh").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "v0.1.1",
            (self.repo / "README.md").read_text(encoding="utf-8"),
        )
        changelog = (self.repo / "CHANGELOG.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## [0.1.0] - 2026-01-01", changelog)

    def test_an_unknown_preset_is_an_error(self) -> None:
        with self.assertRaises(PresetError):
            find_preset(self.presets, self.repo, {"preset": "missing"})

    def test_program_manifest_round_trips_the_preset(self) -> None:
        ledger = Ledger(self.settings.db_path)
        self.addCleanup(ledger.close)
        project_id = create_project(
            self.settings,
            ledger,
            "Preset manifest",
            "A brief.",
            mode="brownfield",
        )
        project = ledger.get_project(project_id)
        assert project is not None
        layout = ProjectLayout.detect(project["workspace"])
        set_entries(
            layout,
            [
                {
                    "id": "web",
                    "role": "frontend",
                    "provider": "local",
                    "url": "",
                    "depends_on": [],
                    "preset": "node",
                }
            ],
        )
        write_program(layout, "preset-manifest", "")
        text = (layout.control / "program.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("preset: node", text)
        self.assertEqual(entries(layout)[0]["preset"], "node")


if __name__ == "__main__":
    unittest.main()
