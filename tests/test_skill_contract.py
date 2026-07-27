from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "openconcierge" / "SKILL.md"


class SkillContractTests(unittest.TestCase):
    def test_frontmatter_has_provider_neutral_metadata(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertRegex(text, r"(?m)^name:\s*openconcierge\s*$")
        self.assertRegex(text, r"(?m)^description:\s*.+$")
        self.assertNotRegex(text, r"(?m)^\s*requires_tools:")
        self.assertNotRegex(text, r"(?m)^\s*requires_toolsets:")
        self.assertNotRegex(text, r"(?i)(requires|depends on).*(exa|tavily|serpapi|serper|brave|duckduckgo)")

    def test_skill_contains_required_workflow_sections(self):
        text = SKILL.read_text(encoding="utf-8")
        for heading in (
            "## When to Use",
            "## Clarifying Questions",
            "## Search Capability Resolution",
            "## Evidence and Ranking",
            "## Recommendation Format",
            "## Memory and Privacy",
            "## Failure Handling",
        ):
            self.assertIn(heading, text)

    def test_skill_does_not_cap_questions(self):
        text = SKILL.read_text(encoding="utf-8").lower()
        self.assertNotRegex(text, r"at most\s+[0-9]+\s+questions")
        self.assertNotIn("1–3", text)
        self.assertNotIn("1-3", text)


if __name__ == "__main__":
    unittest.main()