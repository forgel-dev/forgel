from __future__ import annotations

import re
import unittest
from pathlib import Path

from forgel.environment import command_argv, parse_environment

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "src" / "forgel" / "templates" / "django-drf-react"
QA_COMPOSE = "docker/docker-compose.qa.yml"
E2E_COMMAND = "sh scripts/e2e.sh"

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
    "scripts/e2e.sh",
    "docker/entrypoint.sh",
    QA_COMPOSE,
    "api/manage.py",
    "api/requirements.txt",
    "api/config/settings.py",
    "api/config/urls.py",
    "api/health/urls.py",
    "api/health/views.py",
    "api/tests/test_health.py",
    "web/index.html",
    "web/package.json",
    "web/Dockerfile",
    "web/nginx.conf",
    "web/src/main.jsx",
    "web/src/App.jsx",
    "qa/Dockerfile",
    "qa/package.json",
    "qa/scenario.js",
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
        argv = command_argv(environment.test[0])
        self.assertEqual(argv[0], "sh")
        self.assertEqual(argv[1], "scripts/test.sh")
        wrapper = (TEMPLATE / argv[1]).resolve()
        self.assertTrue(wrapper.is_file(), argv[1])
        body = wrapper.read_text(encoding="utf-8")
        self.assertIn("manage.py", body)
        self.assertIn(" test", body)
        self.assertIn("api", body)

    def test_the_e2e_command_is_declared_and_builds_the_qa_stand(self) -> None:
        environment = parse_environment(self.text, source=str(self.path))
        self.assertTrue(environment.e2e, "environment.yaml declares no e2e")
        self.assertEqual(environment.e2e, (E2E_COMMAND,))
        argv = command_argv(environment.e2e[0])
        self.assertEqual(argv, ["sh", "scripts/e2e.sh"])
        wrapper = (TEMPLATE / argv[1]).resolve()
        self.assertTrue(wrapper.is_file(), E2E_COMMAND)
        body = wrapper.read_text(encoding="utf-8")
        self.assertIn("set -e", body)
        self.assertIn(QA_COMPOSE, body)
        # The wrapper builds the stand, starts api, postgres, object storage
        # and web, runs the scenario from the qa profile and tears the stand
        # down; `set -e` makes a failing step fail the whole command.
        self.assertIn("$compose build", body)
        self.assertIn("up", body)
        self.assertIn("--profile qa run --rm qa", body)
        self.assertIn("down", body)

    def test_the_e2e_command_is_a_well_formed_argument_list(self) -> None:
        environment = parse_environment(self.text, source=str(self.path))
        for command in environment.e2e:
            argv = command_argv(command)
            self.assertTrue(argv)
            self.assertFalse(any("\n" in item for item in argv), argv)
            self.assertEqual(argv[0], "sh")

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

    def test_declares_the_api_web_postgres_and_object_storage(self) -> None:
        self.assertEqual(
            set(self.services), {"api", "web", "postgres", "minio"}
        )
        self.assertIn("postgres:", self.services["postgres"])
        self.assertIn("${S3_ACCESS_KEY", self.services["minio"])

    def test_declares_the_api_postgres_and_object_storage(self) -> None:
        # The backend slice still declares api, postgres and object storage;
        # the SPA adds `web` on top of that set.
        self.assertLessEqual(
            {"api", "postgres", "minio"}, set(self.services)
        )
        self.assertIn("postgres:", self.services["postgres"])
        self.assertIn("${S3_ACCESS_KEY", self.services["minio"])

    def test_declares_the_web_service(self) -> None:
        self.assertIn("web", self.services)

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


class WebAppTest(unittest.TestCase):
    def test_the_spa_fetches_the_health_endpoint(self) -> None:
        app = (TEMPLATE / "web" / "src" / "App.jsx").read_text(
            encoding="utf-8"
        )
        self.assertIn('fetch("/healthz"', app)
        self.assertIn("react", app)
        self.assertIn('data-testid="health-status"', app)

    def test_the_spa_is_bundled_and_served_by_nginx(self) -> None:
        package = (TEMPLATE / "web" / "package.json").read_text(
            encoding="utf-8"
        )
        self.assertIn('"build"', package)
        self.assertIn("esbuild", package)
        self.assertIn('"react"', package)
        dockerfile = (TEMPLATE / "web" / "Dockerfile").read_text(
            encoding="utf-8"
        )
        self.assertIn("npm run build", dockerfile)
        self.assertIn("nginx", dockerfile)
        nginx = (TEMPLATE / "web" / "nginx.conf").read_text(encoding="utf-8")
        self.assertIn("proxy_pass", nginx)
        self.assertIn("api:8000", nginx)

    def test_compose_uses_the_web_image(self) -> None:
        web = services(
            (TEMPLATE / "compose.yaml").read_text(encoding="utf-8")
        )["web"]
        self.assertIn("context: web", web)
        self.assertIn("WEB_PORT", web)


class QaStandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = (TEMPLATE / QA_COMPOSE).read_text(encoding="utf-8")
        self.services = services(self.text)

    def test_the_stand_runs_every_service_of_the_slice(self) -> None:
        self.assertEqual(
            set(self.services), {"api", "postgres", "minio", "web", "qa"}
        )

    def test_the_scenario_runs_in_the_qa_profile(self) -> None:
        self.assertIn("profiles: [qa]", self.services["qa"])

    def test_the_stand_is_isolated_from_the_host_and_the_internet(self) -> None:
        for name, body in self.services.items():
            with self.subTest(service=name):
                self.assertNotIn("ports:", body, name)
                self.assertNotIn("0.0.0.0", body, name)
        self.assertIn("internal: true", self.text)
        self.assertNotIn("yandex", self.text.lower())

    def test_the_browser_scenario_runs_in_a_headless_browser(self) -> None:
        scenario = (TEMPLATE / "qa" / "scenario.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("playwright", scenario)
        self.assertIn("chromium.launch", scenario)
        self.assertIn('pathname === "/healthz"', scenario)
        self.assertIn("health.status() === 200", scenario)
        self.assertIn("health-status", scenario)
        self.assertIn("process.exit", scenario)
        package = (TEMPLATE / "qa" / "package.json").read_text(
            encoding="utf-8"
        )
        self.assertIn("playwright", package)
        dockerfile = (TEMPLATE / "qa" / "Dockerfile").read_text(
            encoding="utf-8"
        )
        self.assertIn("playwright", dockerfile)


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
