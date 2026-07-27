from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DistributionLayoutTests(unittest.TestCase):
    def test_required_distribution_files_exist(self):
        required = (
            ROOT / "distribution.yaml",
            ROOT / "SOUL.md",
            ROOT / "skills" / "openconcierge" / "SKILL.md",
            ROOT / "skills" / "openconcierge" / "references" / "interviewing.md",
            ROOT / "skills" / "openconcierge" / "references" / "research-and-evidence.md",
            ROOT / "skills" / "openconcierge" / "references" / "recommendations.md",
            ROOT / "skills" / "openconcierge" / "references" / "memory-and-privacy.md",
            ROOT / "skills" / "openconcierge" / "scripts" / "rank_candidates.py",
        )
        missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()