from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel.jurisdiction import (
    JurisdictionError,
    load_pack,
    resolve_pack,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class JurisdictionTest(unittest.TestCase):
    def test_ru_draft_is_usable_with_acknowledgement(self) -> None:
        pack = load_pack(REPO_ROOT / "jurisdiction" / "ru.json")
        self.assertEqual(pack.id, "ru")
        self.assertEqual(pack.status, "draft")
        self.assertEqual(pack.region, "ru")
        self.assertTrue(pack.production_allowed)
        self.assertTrue(pack.acknowledgement_required)
        self.assertEqual(pack.legal_review_status, "draft")
        self.assertTrue(pack.requires_human_review)
        self.assertIn("personal-data", pack.categories)

    def test_reviewed_pack_needs_no_acknowledgement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "xx.json"
            path.write_text(
                json.dumps(
                    {
                        "id": "xx",
                        "version": "1.0.0",
                        "status": "reviewed",
                        "region": "xx",
                        "effective_from": "2026-01-01",
                        "reviewed_by": "counsel",
                        "review_due": "2027-01-01",
                        "requires_human_review": False,
                        "data_residency": "required",
                        "legal_sources": [],
                        "categories": [],
                        "mandatory_requirements": [],
                        "prohibitions": [],
                        "required_evidence": [],
                        "notes": "",
                    }
                ),
                encoding="utf-8",
            )
            pack = load_pack(path)
            self.assertTrue(pack.production_allowed)
            self.assertFalse(pack.acknowledgement_required)

    def test_reviewed_pack_without_reviewer_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "xx.json"
            path.write_text(
                json.dumps(
                    {
                        "id": "xx",
                        "version": "1.0.0",
                        "status": "reviewed",
                        "region": "xx",
                        "reviewed_by": None,
                        "review_due": None,
                        "requires_human_review": False,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(JurisdictionError):
                load_pack(path)

    def test_missing_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(JurisdictionError):
                load_pack(Path(tmp) / "missing.json")

    def test_missing_pack_falls_back_to_generic(self) -> None:
        pack, fallback = resolve_pack(REPO_ROOT / "jurisdiction", "zz", "zz")
        self.assertTrue(fallback)
        self.assertEqual(pack.id, "generic")
        self.assertEqual(pack.region, "*")
        self.assertTrue(pack.production_allowed)
        self.assertTrue(pack.acknowledgement_required)


if __name__ == "__main__":
    unittest.main()
