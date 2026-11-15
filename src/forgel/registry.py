"""Recipe registry loading, validation and deterministic matching."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_TEMPLATES_PATH = Path(__file__).resolve().parent / "templates"
KNOWN_STATUSES = frozenset({"draft", "conformant", "deprecated"})


class RegistryError(RuntimeError):
    """Raised when the registry cannot be loaded or a recipe cannot be selected."""


@dataclass(frozen=True)
class Recipe:
    id: str
    version: str
    status: str
    description: str
    composes: tuple[str, ...]
    requires: tuple[str, ...]
    excludes: tuple[str, ...]
    regions: tuple[str, ...]
    template: str

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"


def _version_key(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for part in version.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _is_numeric_version(version: str) -> bool:
    parts = version.split(".")
    if not version or not parts:
        return False
    return all(part.isdigit() for part in parts)


def validate_recipes(
    recipes: list[Recipe], templates_path: Path | None = None
) -> None:
    """Validate loaded recipes, raising :class:`RegistryError` on the first fault.

    The checks are deterministic and follow registry order: duplicate ids,
    malformed ``composes`` entries, non-numeric versions, unknown statuses and
    conformant recipes whose template directory is missing.
    """

    templates = (
        DEFAULT_TEMPLATES_PATH if templates_path is None else Path(templates_path)
    )
    seen: set[str] = set()
    for recipe in recipes:
        if recipe.id in seen:
            raise RegistryError(f"Duplicate recipe id: {recipe.id}")
        seen.add(recipe.id)

        for entry in recipe.composes:
            if "@" not in entry:
                raise RegistryError(
                    f"Recipe {recipe.id}: malformed composes entry {entry!r} "
                    "(expected name@version)"
                )

        if not _is_numeric_version(recipe.version):
            raise RegistryError(
                f"Recipe {recipe.id}: version {recipe.version!r} is not numeric"
            )

        if recipe.status not in KNOWN_STATUSES:
            raise RegistryError(
                f"Recipe {recipe.id}: unknown status {recipe.status!r}; "
                f"expected one of {sorted(KNOWN_STATUSES)}"
            )

        if recipe.status == "conformant" and not (
            templates / recipe.template
        ).is_dir():
            raise RegistryError(
                f"Recipe {recipe.id}: template directory not found: "
                f"{templates / recipe.template}"
            )


def load_registry(
    path: Path, templates_path: Path | None = None
) -> list[Recipe]:
    """Load and validate recipes from a JSON registry file."""

    if not path.exists():
        raise RegistryError(f"Registry not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RegistryError(f"Registry is not valid JSON: {path}: {exc}") from exc

    recipes: list[Recipe] = []
    for item in data.get("recipes", []):
        constraints = item.get("constraints", {})
        recipes.append(
            Recipe(
                id=str(item["id"]),
                version=str(item["version"]),
                status=str(item.get("status", "draft")),
                description=str(item.get("description", "")),
                composes=tuple(str(value) for value in item.get("composes", [])),
                requires=tuple(str(value) for value in constraints.get("requires", [])),
                excludes=tuple(str(value) for value in constraints.get("excludes", [])),
                regions=tuple(str(value) for value in constraints.get("regions", [])),
                template=str(item["template"]),
            )
        )
    if not recipes:
        raise RegistryError(f"Registry contains no recipes: {path}")
    validate_recipes(recipes, templates_path)
    return recipes


def select_recipe(
    recipes: list[Recipe], requirements: dict[str, Any]
) -> Recipe:
    """Select the highest-version conformant recipe that satisfies the requirements.

    Matching is deterministic and deliberately simple: required capabilities must
    be a subset of the recipe's capabilities; excluded capabilities must not
    overlap; the region must be allowed when the recipe declares regions.
    """

    required = set(requirements.get("requires", []))
    excluded = set(requirements.get("excludes", []))
    region = requirements.get("region")

    candidates: list[Recipe] = []
    for recipe in recipes:
        if recipe.status != "conformant":
            continue
        if not required.issubset(set(recipe.requires)):
            continue
        if excluded & set(recipe.requires):
            continue
        if set(recipe.excludes) & required:
            continue
        if region and recipe.regions and region not in recipe.regions:
            continue
        candidates.append(recipe)

    if not candidates:
        raise RegistryError(
            "No recipe matches the requirements: "
            f"requires={sorted(required)}, excludes={sorted(excluded)}, region={region!r}"
        )
    return max(candidates, key=lambda recipe: _version_key(recipe.version))
