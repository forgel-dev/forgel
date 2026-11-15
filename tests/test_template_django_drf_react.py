from __future__ import annotations

import re
import unittest
from pathlib import Path

from forgel.environment import parse_environment

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "src" / "forgel" / "templates" / "django-drf-react"

REQUIRED_FILES = (
    "FORGEL.md",
    "AGENTS.md",
    "README.md",
    ".gitignore",
    ".dockerignore",
    ".env.example",
    "Dockerfile",
    "compose.yaml",
    "environment.yaml",
    "scripts/test.sh",
    "docker/entrypoint.sh",
    "api/manage.py",
    "api/requirements.txt",
    "api/config/settings.py",
    "api/config/urls.py",
    "api/health/urls.py",
    "api/health/views.py",
    "api/tests/test_health.py",
)

PINNED = (
    "Django==",
    "djangorestframework==",
    "psycopg",
    "django-storages==",
    "boto3==",
)

SERVICE_LINE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")


def services(compose_text: str) -> dict[str, str]:
    """Map each service under ``services:`` to its indented entry lines."""

    found: dict[str, str] = {}
    current: str | None = None
    in_services = False
    for line in compose_text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            in_services = line.split(":", 1)[0].strip() == "services"
            current = None
            continue
        if not in_services:
            continue
        match = SERVICE_LINE.match(line)
        if match:
            current = match.group(1)
            found[current] = ""
            continue
        if current is not None:
            found[current] += line.strip() + "\n"
    return found


class TemplateLayoutTest(unittest.TestCase):
    def test_the_template_directory_exists(self) -> None:
        self.assertTrue(TEMPLATE.is_dir(), f"missing template: {TEMPLATE}")

    def test_required_files_are_present(self) -> None:
        missing = [
            name for name in REQUIRED_FILES if not (TEMPLATE / name).is_file()
        ]
        self.assertEqual(missing, [], f"missing template files: {missing}")

    def test_requirement_pins_are_declared(self) -> None:
        text = (TEMPLATE / "api" / "requirements.txt").read_text(
            encoding="utf-8"
        )
        for pin in PINNED:
            self.assertIn(pin, text)

    def test_python_sources_compile(self) -> None:
        sources = [
            path
            for path in TEMPLATE.rglob("*.py")
            if "__pycache__" not in path.parts
        ]
        self.assertTrue(sources)
        for path in sources:
            with self.subTest(path=str(path.relative_to(TEMPLATE))):
                compile(path.read_text(encoding="utf-8"), str(path), "exec")

    def test_settings_read_database_and_storage_from_the_environment(self) -> None:
        text = (TEMPLATE / "api" / "config" / "settings.py").read_text(
            encoding="utf-8"
        )
        for name in (
            "DATABASE_URL",
            "POSTGRES_HOST",
            "POSTGRES_DB",
            "S3_ENDPOINT",
            "S3_BUCKET",
            "S3_ACCESS_KEY",
            "S3_SECRET_KEY",
        ):
            self.assertIn(name, text)
        self.assertIn("django.db.backends.postgresql", text)
        self.assertIn("storages.backends.s3.S3Storage", text)

    def test_the_template_does_not_depend_on_the_hello_web_recipe(self) -> None:
        for path in TEMPLATE.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("hello-web", text, str(path))
            self.assertNotIn("hello_web", text, str(path))


class TemplateEnvironmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.path = TEMPLATE / "environment.yaml"
        self.text = self.path.read_text(encoding="utf-8")

    def test_the_contract_parses(self) -> None:
        environment = parse_environment(
            self.text, source=str(self.path), base=TEMPLATE
        )
        self.assertTrue(environment.image or environment.build)
        self.assertEqual(environment.services, ("compose.yaml",))
        self.assertEqual(environment.ports, (8000,))
        self.assertEqual(environment.health, "/healthz")

    def test_the_test_command_is_declared_and_runs_from_api(self) -> None:
        environment = parse_environment(self.text, source=str(self.path))
        self.assertTrue(environment.test, "environment.yaml declares no test")
        self.assertEqual(environment.e2e, (), "e2e belongs to a later task")
        command = environment.test[0]
        self.assertIn("manage.py", command + self._wrapper_text(command))
        wrapper = (TEMPLATE / command.lstrip("./")).resolve()
        self.assertTrue(wrapper.is_file(), command)
        body = wrapper.read_text(encoding="utf-8")
        self.assertIn("manage.py", body)
        self.assertIn(" test", body)
        self.assertIn("api", body)

    def _wrapper_text(self, command: str) -> str:
        wrapper = (TEMPLATE / command.lstrip("./")).resolve()
        if not wrapper.is_file():
            return ""
        return wrapper.read_text(encoding="utf-8")

    def test_the_declared_artifacts_exist(self) -> None:
        environment = parse_environment(self.text, source=str(self.path))
        for service in environment.services:
            self.assertTrue((TEMPLATE / service).is_file(), service)
        for command in environment.setup:
            self.assertIn("api/requirements.txt", command)


class ComposeServicesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = (TEMPLATE / "compose.yaml").read_text(encoding="utf-8")
        self.services = services(self.text)

    def test_declares_the_api_postgres_and_object_storage(self) -> None:
        self.assertEqual(set(self.services), {"api", "postgres", "minio"})

    def test_postgres_is_configured_from_the_environment(self) -> None:
        postgres = self.services["postgres"]
        self.assertIn("postgres:", postgres)
        self.assertIn("${POSTGRES_DB", postgres)
        self.assertIn("${POSTGRES_USER", postgres)
        self.assertIn("${POSTGRES_PASSWORD", postgres)

    def test_object_storage_is_configured_from_the_environment(self) -> None:
        minio = self.services["minio"]
        self.assertIn("image: ${MINIO_IMAGE", minio)
        self.assertIn("${S3_ACCESS_KEY", minio)
        self.assertIn("${S3_SECRET_KEY", minio)

    def test_the_default_object_storage_image_is_minio(self) -> None:
        minio = self.services["minio"]
        default_image = re.search(
            r"image: \$\{MINIO_IMAGE:-([^}]+)\}", minio
        )
        self.assertIsNotNone(default_image, minio)
        self.assertIn("minio", default_image.group(1))

    def test_the_api_is_wired_to_both_services(self) -> None:
        api = self.services["api"]
        self.assertIn("postgres", api)
        self.assertIn("minio", api)
        self.assertIn("S3_ENDPOINT", api)
        self.assertIn("POSTGRES_HOST", api)
        self.assertIn("${S3_BUCKET", api)

    def test_the_bucket_is_created_on_startup(self) -> None:
        entrypoint = (TEMPLATE / "docker" / "entrypoint.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("config.bucket", entrypoint)
        bucket = (TEMPLATE / "api" / "config" / "bucket.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("create_bucket", bucket)
        self.assertIn("S3_BUCKET", bucket)

    def test_no_credential_literals_are_committed(self) -> None:
        env_example = (TEMPLATE / ".env.example").read_text(encoding="utf-8")
        self.assertIn("S3_SECRET_KEY=", env_example)
        self.assertIn("POSTGRES_PASSWORD=", env_example)
        ignore = (TEMPLATE / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".env", ignore.splitlines())


class HealthRouteTest(unittest.TestCase):
    def test_the_health_route_is_registered(self) -> None:
        root = (TEMPLATE / "api" / "config" / "urls.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('include("health.urls")', root)
        app = (TEMPLATE / "api" / "health" / "urls.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('path("healthz"', app)
        self.assertIn('name="healthz"', app)

    def test_the_health_view_is_a_drf_endpoint(self) -> None:
        text = (TEMPLATE / "api" / "health" / "views.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("rest_framework", text)
        self.assertIn('{"status": "ok"}', text)

    def test_django_tests_use_the_client_without_services(self) -> None:
        text = (TEMPLATE / "api" / "tests" / "test_health.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('self.client.get("/healthz")', text)
        self.assertIn("TestCase", text)
        settings = (TEMPLATE / "api" / "config" / "settings.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("sqlite3", settings)


if __name__ == "__main__":
    unittest.main()
