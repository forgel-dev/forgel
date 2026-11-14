from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from forgel.environment import (
    Environment,
    EnvironmentError,
    command_argv,
    environment_path,
    load_environment,
    parse_environment,
    parse_yaml,
    render_environment,
)
from forgel.layout import ProjectLayout

REPO_ROOT = Path(__file__).resolve().parents[1]

FULL = """
# the project environment
image: python:3.12-slim
repo: api
mounts: [web]
services: [compose.yaml, "infra/extra.yml"]
setup:
  - pip install -r requirements.txt
test: ["python -m unittest discover -s tests"]
e2e: python e2e/check.py
ports: [8000, 8443]
health: "/health"
"""


class ParseEnvironmentTest(unittest.TestCase):
    def test_parses_every_contract_field(self) -> None:
        environment = parse_environment(FULL)
        self.assertEqual(environment.image, "python:3.12-slim")
        self.assertEqual(environment.repo, "api")
        self.assertEqual(environment.mounts, ("web",))
        self.assertEqual(
            environment.services, ("compose.yaml", "infra/extra.yml")
        )
        self.assertEqual(
            environment.setup, ("pip install -r requirements.txt",)
        )
        self.assertEqual(
            environment.test,
            ("python -m unittest discover -s tests",),
        )
        self.assertEqual(environment.e2e, ("python e2e/check.py",))
        self.assertEqual(environment.ports, (8000, 8443))
        self.assertEqual(environment.health, "/health")

    def test_image_may_contain_a_colon(self) -> None:
        environment = parse_environment("image: python:3.12-slim\n")
        self.assertEqual(environment.image, "python:3.12-slim")

    def test_block_list_and_flow_list_are_equivalent(self) -> None:
        block = parse_environment(
            "image: x\nsetup:\n  - pip install a\n  - pip install b\n"
        )
        flow = parse_environment(
            'image: x\nsetup: ["pip install a", "pip install b"]\n'
        )
        self.assertEqual(block.setup, flow.setup)

    def test_build_is_an_alternative_to_image(self) -> None:
        environment = parse_environment("build: repos/api/environment\n")
        self.assertEqual(environment.build, "repos/api/environment")
        self.assertEqual(environment.image, "")

    def test_single_command_string_is_normalized(self) -> None:
        environment = parse_environment("image: x\ntest: python -m unittest\n")
        self.assertEqual(environment.commands("test"), ("python -m unittest",))

    def test_comments_and_quotes(self) -> None:
        data = parse_yaml(
            "image: x  # comment\n"
            "health: '/health'\n"
            'setup: ["pip install \\"a#b\\""]  # trailing\n'
        )
        self.assertEqual(data["health"], "/health")
        self.assertEqual(data["setup"], ['pip install "a#b"'])
        self.assertEqual(data["image"], "x")

    def test_env_mapping_is_parsed(self) -> None:
        environment = parse_environment(
            "image: x\nenv:\n  PYTHONPATH: src\n  FOO: bar\n"
        )
        self.assertEqual(
            environment.env_map, {"PYTHONPATH": "src", "FOO": "bar"}
        )

    def test_env_cannot_override_the_sandbox_home(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("image: x\nenv:\n  HOME: /root\n")

    def test_invalid_env_name_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("image: x\nenv:\n  1BAD: value\n")

    def test_env_must_be_a_mapping(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("image: x\nenv: PYTHONPATH=src\n")

    def test_empty_contract_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("")

    def test_image_and_build_together_are_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("image: x\nbuild: repos/api\n")

    def test_unknown_field_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError) as ctx:
            parse_environment("image: x\ncommand: make test\n")
        self.assertIn("unknown field", str(ctx.exception))

    def test_duplicate_key_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("image: x\nimage: y\n")

    def test_unexpected_indentation_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("image: x\n  nested: y\n")

    def test_unterminated_flow_list_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("image: x\nports: [8000\n")

    def test_absolute_build_path_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("build: /etc/environment\n")

    def test_escaping_build_path_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("build: ../outside\n")

    def test_invalid_ports_are_rejected(self) -> None:
        for ports in ("[0]", "[70000]", "[abc]"):
            with self.subTest(ports=ports):
                with self.assertRaises(EnvironmentError):
                    parse_environment(f"image: x\nports: {ports}\n")

    def test_invalid_health_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("image: x\nhealth: healthz\n")

    def test_invalid_repo_name_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("image: x\nrepo: ../main\n")

    def test_mounting_the_working_repository_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            parse_environment("image: x\nrepo: api\nmounts: [api]\n")

    def test_render_round_trips(self) -> None:
        environment = Environment(
            image="python:3.12-slim",
            repo="api",
            mounts=("web",),
            services=("compose.yaml",),
            setup=("pip install -r requirements.txt",),
            test=("python -m unittest",),
            e2e=("python e2e/check.py",),
            env=(("PYTHONPATH", "src"),),
            ports=(8000,),
            health="/health",
        )
        self.assertEqual(
            parse_environment(render_environment(environment)), environment
        )


class LoadEnvironmentTest(unittest.TestCase):
    def _layout(self, root: Path, kind: str = "legacy") -> ProjectLayout:
        return ProjectLayout(root=root, kind=kind)

    def test_missing_contract_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(load_environment(self._layout(root)))

    def test_legacy_contract_is_loaded_from_the_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            environment_path(self._layout(root)).write_text(
                "image: python:3.12-slim\ntest: python -m unittest\n",
                encoding="utf-8",
            )
            environment = load_environment(self._layout(root))
            self.assertIsNotNone(environment)
            assert environment is not None
            self.assertEqual(environment.test, ("python -m unittest",))

    def test_malformed_contract_raises_instead_of_falling_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "environment.yaml").write_text(
                "image: x\nunknown: y\n", encoding="utf-8"
            )
            with self.assertRaises(EnvironmentError):
                load_environment(self._layout(root))

    def test_unknown_repository_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project.json").write_text(
                json.dumps({"repos": [{"id": "main"}]}), encoding="utf-8"
            )
            (root / "repos" / "main").mkdir(parents=True)
            (root / "program").mkdir()
            (root / "program" / "environment.yaml").write_text(
                "image: x\nrepo: other\n", encoding="utf-8"
            )
            with self.assertRaises(EnvironmentError):
                load_environment(self._layout(root, "container"))

    def test_sole_repository_is_the_default_workdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project.json").write_text(
                json.dumps({"repos": [{"id": "main"}]}), encoding="utf-8"
            )
            (root / "repos" / "main").mkdir(parents=True)
            (root / "program").mkdir()
            (root / "program" / "environment.yaml").write_text(
                "image: x\ntest: python -m unittest\n", encoding="utf-8"
            )
            layout = self._layout(root, "container")
            environment = load_environment(layout)
            assert environment is not None
            self.assertEqual(environment.repository(layout), "main")
            self.assertEqual(environment.workdir(layout), root / "repos" / "main")

    def test_explicit_repository_is_the_workdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project.json").write_text(
                json.dumps({"repos": [{"id": "api"}, {"id": "web"}]}),
                encoding="utf-8",
            )
            for repo in ("api", "web"):
                (root / "repos" / repo).mkdir(parents=True)
            (root / "program").mkdir()
            (root / "program" / "environment.yaml").write_text(
                "image: x\nrepo: web\n", encoding="utf-8"
            )
            layout = self._layout(root, "container")
            environment = load_environment(layout)
            assert environment is not None
            self.assertEqual(environment.workdir(layout), root / "repos" / "web")

    def test_several_repositories_default_to_the_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project.json").write_text(
                json.dumps({"repos": [{"id": "api"}, {"id": "web"}]}),
                encoding="utf-8",
            )
            for repo in ("api", "web"):
                (root / "repos" / repo).mkdir(parents=True)
            (root / "program").mkdir()
            (root / "program" / "environment.yaml").write_text(
                "image: x\n", encoding="utf-8"
            )
            layout = self._layout(root, "container")
            environment = load_environment(layout)
            assert environment is not None
            self.assertEqual(environment.repository(layout), "")
            self.assertEqual(environment.workdir(layout), root)

    def test_a_single_repository_contract_is_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project.json").write_text(
                json.dumps({"repos": [{"id": "main"}]}), encoding="utf-8"
            )
            repo = root / "repos" / "main"
            (repo / "environment").mkdir(parents=True)
            (repo / "environment" / "Dockerfile").write_text("FROM scratch\n")
            (repo / "environment.yaml").write_text(
                "build: environment\n"
                "test: python -m unittest\n"
                "env:\n  PYTHONPATH: src\n",
                encoding="utf-8",
            )
            (root / "program").mkdir()
            layout = self._layout(root, "container")
            environment = load_environment(layout)
            assert environment is not None
            self.assertEqual(environment.base, repo)
            self.assertEqual(environment.env_map, {"PYTHONPATH": "src"})
            self.assertEqual(environment.test, ("python -m unittest",))

    def test_the_control_repository_contract_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project.json").write_text(
                json.dumps({"repos": [{"id": "main"}]}), encoding="utf-8"
            )
            repo = root / "repos" / "main"
            repo.mkdir(parents=True)
            (root / "program").mkdir()
            (root / "program" / "environment.yaml").write_text(
                "image: control\n", encoding="utf-8"
            )
            (repo / "environment.yaml").write_text(
                "image: repo\n", encoding="utf-8"
            )
            environment = load_environment(self._layout(root, "container"))
            assert environment is not None
            self.assertEqual(environment.image, "control")

    def test_unknown_mount_repository_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project.json").write_text(
                json.dumps({"repos": [{"id": "main"}]}), encoding="utf-8"
            )
            (root / "repos" / "main").mkdir(parents=True)
            (root / "program").mkdir()
            (root / "program" / "environment.yaml").write_text(
                "image: x\nmounts: [other]\n", encoding="utf-8"
            )
            with self.assertRaises(EnvironmentError):
                load_environment(self._layout(root, "container"))

    def test_missing_build_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "environment.yaml").write_text(
                "build: environment\n", encoding="utf-8"
            )
            with self.assertRaises(EnvironmentError):
                load_environment(self._layout(root))


class RepositoryEnvironmentTest(unittest.TestCase):
    def test_the_repository_environment_contract_is_valid(self) -> None:
        layout = ProjectLayout(root=REPO_ROOT, kind="legacy")
        environment = load_environment(layout)
        self.assertIsNotNone(environment)
        assert environment is not None
        self.assertEqual(environment.build, "environment")
        self.assertEqual(
            environment.test, ("python -m unittest discover -s tests",)
        )
        self.assertEqual(environment.env_map, {"PYTHONPATH": "src"})
        self.assertTrue((REPO_ROOT / "environment" / "Dockerfile").is_file())


class CommandArgvTest(unittest.TestCase):
    def test_python_is_resolved_to_the_running_interpreter(self) -> None:
        self.assertEqual(
            command_argv("python -m unittest discover"),
            [sys.executable, "-m", "unittest", "discover"],
        )

    def test_other_executables_are_kept(self) -> None:
        self.assertEqual(command_argv("node check.mjs"), ["node", "check.mjs"])

    def test_empty_command_is_rejected(self) -> None:
        with self.assertRaises(EnvironmentError):
            command_argv("   ")


if __name__ == "__main__":
    unittest.main()
