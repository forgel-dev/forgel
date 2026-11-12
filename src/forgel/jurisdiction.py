"""Jurisdiction pack loading and advisory production rules.

The layer informs the spec, QA and the production gate. It does not block a
deploy on its own: a draft pack is better than an ignored jurisdiction, and the
human who approves production carries responsibility for compliance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VALID_STATUSES = {"draft", "reviewed", "expired"}


class JurisdictionError(RuntimeError):
    """Raised when a jurisdiction pack is missing or invalid."""


@dataclass(frozen=True)
class JurisdictionPack:
    id: str
    version: str
    status: str
    region: str
    effective_from: str | None
    reviewed_by: str | None
    review_due: str | None
    requires_human_review: bool
    data_residency: str
    legal_sources: tuple[dict[str, Any], ...]
    categories: tuple[str, ...]
    mandatory_requirements: tuple[dict[str, Any], ...]
    prohibitions: tuple[str, ...]
    required_evidence: tuple[str, ...]
    notes: str

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"

    @property
    def legal_review_status(self) -> str:
        return self.status

    @property
    def acknowledgement_required(self) -> bool:
        """Reviewed packs do not need the compliance acknowledgement."""

        return not (self.status == "reviewed" and not self.requires_human_review)

    @property
    def production_allowed(self) -> bool:
        """The layer informs; the human production gate decides. It never blocks."""

        return True


def load_pack(path: Path) -> JurisdictionPack:
    if not path.exists():
        raise JurisdictionError(f"Jurisdiction pack not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise JurisdictionError(
            f"Jurisdiction pack is not valid JSON: {path}: {exc}"
        ) from exc

    status = str(data.get("status", "draft"))
    if status not in VALID_STATUSES:
        raise JurisdictionError(
            f"Jurisdiction pack {path} has invalid status {status!r}; "
            f"expected one of {sorted(VALID_STATUSES)}"
        )
    if status == "reviewed" and (
        not data.get("reviewed_by") or not data.get("review_due")
    ):
        raise JurisdictionError(
            f"Reviewed pack {path} must declare reviewed_by and review_due"
        )

    return JurisdictionPack(
        id=str(data["id"]),
        version=str(data["version"]),
        status=status,
        region=str(data["region"]),
        effective_from=data.get("effective_from"),
        reviewed_by=data.get("reviewed_by"),
        review_due=data.get("review_due"),
        requires_human_review=bool(data.get("requires_human_review", True)),
        data_residency=str(data.get("data_residency", "to-be-confirmed")),
        legal_sources=tuple(data.get("legal_sources", [])),
        categories=tuple(str(item) for item in data.get("categories", [])),
        mandatory_requirements=tuple(data.get("mandatory_requirements", [])),
        prohibitions=tuple(str(item) for item in data.get("prohibitions", [])),
        required_evidence=tuple(str(item) for item in data.get("required_evidence", [])),
        notes=str(data.get("notes", "")),
    )


def resolve_pack(
    directory: Path, pack_id: str, region: str
) -> tuple[JurisdictionPack, bool]:
    """Load the requested pack, or the generic draft if it is missing.

    Returns the pack and whether the generic fallback was used. A draft is
    better than an ignored jurisdiction: the core records the gap and proceeds.
    """

    path = directory / f"{pack_id}.json"
    fallback = False
    if path.exists():
        pack = load_pack(path)
    else:
        pack = load_pack(directory / "generic.json")
        fallback = True
    if pack.region not in (region, "*"):
        raise JurisdictionError(
            f"Jurisdiction pack {pack.id} is for region {pack.region}, "
            f"but the requirements say {region}"
        )
    return pack, fallback
