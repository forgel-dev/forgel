from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel.registry import (
    RegistryError,
    load_registry,
    select_recipe,
    validate_recipes,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = REPO_ROOT / "registry" / "recipes.json"
TEMPLATES = REPO_ROOT / "src" / "forgel" / "templates"

STACK_REQUIREMENTS = {
    "requires": ["web", "django", "react", "postgres", "object-storage"],
}


def _write_registry(path: Path, recipes: list[dict[str, object]]) -> Path:
    path.write_text(json.dumps({"recipes": recipes}), encoding="utf-8")
    return path


def _recipe(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "sample",
        "version": "0.1.0",
        "status": "conformant",
        "description": "sample recipe",
        "composes": ["stack-python-stdlib@0.1"],
        "constraints": {"requires": ["web"], "regions": ["ru"]},
        "template": "hello-web",
    }
    data.update(overrides)
    return data


class RegistryTest(unittest.TestCase):
    def test_load_and_select(self) -> None:
        recipes = load_registry(REGISTRY)
        selected = select_recipe(recipes, {"requires": ["web"], "region": "ru"})
        self.assertEqual(selected.id, "hello-web")
        self.assertEqual(selected.ref, "hello-web@0.1.0")

    def test_django_stack_recipe_is_registered(self) -> None:
        recipes = load_registry(REGISTRY)
        recipe = next(item for item in recipes if item.id == "django-drf-react")
        self.assertEqual(recipe.version, "0.1.0")
        self.assertEqual(recipe.status, "conformant")
        self.assertEqual(recipe.template, "django-drf-react")
        self.assertEqual(
            recipe.composes,
            (
                "stack-django-drf@0.1",
                "frontend-react@0.1",
                "db-postgres@0.1",
                "storage-s3@0.1",
                "provider-yandex@0.1",
                "qa-browser@0.1",
            ),
        )
        self.assertEqual(
            recipe.requires,
            ("web", "django", "react", "postgres", "object-storage"),
        )
        self.assertEqual(recipe.regions, ("ru",))
        self.assertEqual(recipe.excludes, ("mobile", "regulated"))

    def test_django_stack_is_selected_for_ru(self) -> None:
        recipes = load_registry(REGISTRY)
        requirements = dict(STACK_REQUIREMENTS, region="ru")
        selected = select_recipe(recipes, requirements)
        self.assertEqual(selected.id, "django-drf-react")
        self.assertEqual(selected.ref, "django-drf-react@0.1.0")

    def test_django_stack_is_not_selected_for_us(self) -> None:
        recipes = load_registry(REGISTRY)
        with self.assertRaises(RegistryError):
            select_recipe(recipes, dict(STACK_REQUIREMENTS, region="us"))

    def test_missing_capability_is_rejected(self) -> None:
        recipes = load_registry(REGISTRY)
        with self.assertRaises(RegistryError):
            select_recipe(recipes, {"requires": ["mobile"], "region": "ru"})

    def test_unknown_region_is_rejected(self) -> None:
        recipes = load_registry(REGISTRY)
        with self.assertRaises(RegistryError):
            select_recipe(recipes, {"requires": ["web"], "region": "mars"})

    def test_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RegistryError):
                load_registry(Path(tmp) / "missing.json")

    def test_empty_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "recipes.json"
            path.write_text('{"recipes": []}', encoding="utf-8")
            with self.assertRaises(RegistryError):
                load_registry(path)

    def test_validate_rejects_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_registry(
                Path(tmp) / "recipes.json",
                [_recipe(), _recipe()],
            )
            with self.assertRaises(RegistryError) as caught:
                load_registry(path, TEMPLATES)
            self.assertIn("Duplicate recipe id", str(caught.exception))

    def test_validate_rejects_missing_template_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_registry(
                Path(tmp) / "recipes.json",
                [_recipe(id="ghost", template="does-not-exist")],
            )
            with self.assertRaises(RegistryError) as caught:
                load_registry(path, TEMPLATES)
            self.assertIn("template directory not found", str(caught.exception))

    def test_validate_rejects_malformed_composes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_registry(
                Path(tmp) / "recipes.json",
                [_recipe(composes=["stack-python-stdlib"])],
            )
            with self.assertRaises(RegistryError) as caught:
                load_registry(path, TEMPLATES)
            self.assertIn("malformed composes entry", str(caught.exception))

    def test_validate_rejects_non_numeric_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_registry(
                Path(tmp) / "recipes.json", [_recipe(version="latest")]
            )
            with self.assertRaises(RegistryError) as caught:
                load_registry(path, TEMPLATES)
            self.assertIn("not numeric", str(caught.exception))

    def test_validate_rejects_unknown_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_registry(
                Path(tmp) / "recipes.json", [_recipe(status="blessed")]
            )
            with self.assertRaises(RegistryError) as caught:
                load_registry(path, TEMPLATES)
            self.assertIn("unknown status", str(caught.exception))

    def test_validate_accepts_draft_without_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            recipes = load_registry(
                _write_registry(
                    Path(tmp) / "recipes.json",
                    [_recipe(status="draft", template="does-not-exist")],
                ),
                TEMPLATES,
            )
            validate_recipes(recipes, TEMPLATES)
            self.assertEqual(recipes[0].status, "draft")


if __name__ == "__main__":
    unittest.main()
