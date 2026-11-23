from __future__ import annotations

import unittest

from forgel import requirements


class RequirementsTemplateTest(unittest.TestCase):
    def test_the_universal_template_has_every_section(self) -> None:
        text = requirements.template_text()
        for heading in (
            "## Document Information",
            "## Overview",
            "## Goals",
            "## Non-Goals",
            "## User Decisions",
            "## Functional Requirements",
            "## User Stories",
            "## Acceptance Criteria",
            "## Scope Boundaries",
            "## Risks",
            "## Open Questions",
            "## Assumptions",
            "## Related Documents",
            "## Revision History",
        ):
            self.assertIn(heading, text)

    def test_render_fills_every_placeholder(self) -> None:
        values = {
            "kind": "Feature",
            "title": "Demo",
            "project": "p1",
            "task": "t1",
            "plan": "plan1",
            "repository": "main",
            "depends_on": "none",
            "status": "New",
            "version": "1.0.0",
            "created": "2026-11-17",
            "source": "test",
            "author": "test",
            "overview": "overview",
            "goals": "- goal",
            "non_goals": "- none",
            "user_decisions": requirements.decisions_table(
                [("D-001", "decision", "user")]
            ),
            "functional_requirements": requirements.numbered(
                "FR", ["requirement"]
            ),
            "technical_requirements": "- constraint",
            "user_stories": "- story",
            "tests": "- test",
            "acceptance": requirements.numbered("AC", ["criterion"]),
            "scope": "- scope",
            "risks": "- risk",
            "open_questions": "- none",
            "affected_files": "- file",
            "assumptions": "- none",
            "related_documents": "- doc",
            "revision_history": "- 1.0.0",
        }
        text = requirements.render(values)
        self.assertNotIn("{{", text)
        self.assertIn("# Feature: Demo", text)
        self.assertIn("| D-001 | decision | user |", text)
        self.assertIn("**FR-1**: requirement", text)
        self.assertIn("**AC-1**: criterion", text)


if __name__ == "__main__":
    unittest.main()
