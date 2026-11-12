from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.registry import RegistryError, load_registry, select_recipe

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = REPO_ROOT / "registry" / "recipes.json"


class RegistryTest(unittest.TestCase):
    def test_load_and_select(self) -> None:
        recipes = load_registry(REGISTRY)
        selected = select_recipe(recipes, {"requires": ["web"], "region": "ru"})
        self.assertEqual(selected.id, "hello-web")
        self.assertEqual(selected.ref, "hello-web@0.1.0")

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


if __name__ == "__main__":
    unittest.main()
