"""Documentation status markers in PLAN.md section 10 and README.md.

M0 and M0.5 are recorded as done/partial with evidence that exists in the
repository tree, and README.md carries the same status wording.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "PLAN.md"
README = ROOT / "README.md"

M0_HEADING = "### M0 \u2014 Skeleton (2\u20133 weeks)"
M0_5_HEADING = "### M0.5 \u2014 Self-Hosting (immediate goal)"

STATUS_RE = re.compile(r"^\*\*Status:\*\* (done|partial) \u2014 \S")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section_lines(text: str, heading: str) -> list[str]:
    """Lines under an exact level-3 heading, up to the next heading or rule."""
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index
            break
    if start is None:
        raise AssertionError(f"heading not found: {heading}")
    body: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("## ") or line.startswith("### ") or line.strip() == "---":
            break
        body.append(line)
    return body


def status_line(text: str, heading: str) -> str:
    """The first non-empty line under a heading."""
    for line in section_lines(text, heading):
        if line.strip():
            return line.strip()
    raise AssertionError(f"no content under {heading}")


class PlanRoadmapStatusTest(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = read(PLAN)

    def test_status_line_directly_under_m0(self) -> None:
        self.assertRegex(status_line(self.plan, M0_HEADING), STATUS_RE)

    def test_status_line_directly_under_m0_5(self) -> None:
        self.assertRegex(status_line(self.plan, M0_5_HEADING), STATUS_RE)

    def test_m0_is_done_with_evidence(self) -> None:
        line = status_line(self.plan, M0_HEADING)
        self.assertTrue(line.startswith("**Status:** done \u2014 "), line)
        for evidence in ("Makefile", "src/forgel/telegram.py", "src/forgel/approvals.py"):
            self.assertIn(evidence, line)

    def test_m0_5_is_partial_with_remaining_work(self) -> None:
        line = status_line(self.plan, M0_5_HEADING)
        self.assertTrue(line.startswith("**Status:** partial \u2014 "), line)
        self.assertIn("what remains", line)
        for evidence in (
            "src/forgel/telegram.py",
            "src/forgel/planner.py",
            "src/forgel/task_qa.py",
            "src/forgel/peak.py",
            "src/forgel/sandbox.py",
        ):
            self.assertIn(evidence, line)

    def test_later_milestones_are_unchanged(self) -> None:
        for heading in (
            "### M1 \u2014 Vertical Slice and Public OSS Alpha (up to 3 months)",
            "### M2 \u2014 Plugins and Ecosystem (4\u20136 months)",
            "### M3 \u2014 Hosted Version (7\u20139 months)",
            "### M4 \u2014 Operations (10\u201312 months)",
        ):
            self.assertIn(heading, self.plan)


class ReadmeStatusTest(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = read(PLAN)
        self.readme = read(README)

    def plan_status(self, heading: str) -> str:
        match = STATUS_RE.match(status_line(self.plan, heading))
        self.assertIsNotNone(match, f"malformed status line under {heading}")
        return match.group(1)

    def test_readme_repeats_m0_and_m0_5_status(self) -> None:
        self.assertIn(f"M0 \u2014 Skeleton: {self.plan_status(M0_HEADING)}", self.readme)
        self.assertIn(
            f"M0.5 \u2014 Self-Hosting: {self.plan_status(M0_5_HEADING)}",
            self.readme,
        )

    def test_readme_links_to_plan_roadmap(self) -> None:
        self.assertIn("PLAN.md#10-roadmap", self.readme)

    def test_readme_names_the_same_remaining_work(self) -> None:
        self.assertIn("post-merge smoke with auto-revert", self.readme)
        self.assertIn("post-merge smoke with auto-revert", self.plan)


class EvidenceExistsTest(unittest.TestCase):
    """Each module named as status evidence must exist in the tree."""

    def test_evidence_files_exist(self) -> None:
        for relative in (
            "src/forgel/telegram.py",
            "src/forgel/planner.py",
            "src/forgel/task_qa.py",
            "src/forgel/peak.py",
            "src/forgel/sandbox.py",
            "src/forgel/adopt.py",
            "src/forgel/deploy.py",
            "src/forgel/providers/github.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_make_demo_target_exists(self) -> None:
        makefile = read(ROOT / "Makefile")
        self.assertRegex(makefile, r"(?m)^demo:")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
