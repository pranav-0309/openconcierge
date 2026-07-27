from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _parse_distribution_yaml(text):
    """Parse the tiny distribution.yaml shape: top-level `key: value` and `key:` followed by indented `- value` list entries."""
    result = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if ":" not in stripped:
            i += 1
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if value:
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            result[key] = value
            i += 1
        else:
            items = []
            i += 1
            while i < len(lines):
                list_line = lines[i]
                list_stripped = list_line.strip()
                if not list_stripped:
                    i += 1
                    continue
                if list_stripped.startswith("- "):
                    items.append(list_stripped[2:].strip())
                    i += 1
                else:
                    break
            result[key] = items
    return result


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

    def test_distribution_manifest_and_identity(self):
        manifest_path = ROOT / "distribution.yaml"
        self.assertTrue(manifest_path.is_file(), "distribution.yaml must exist")
        manifest = _parse_distribution_yaml(manifest_path.read_text(encoding="utf-8"))

        for key in ("name", "version", "description", "hermes_requires"):
            self.assertIn(key, manifest, f"distribution.yaml must declare {key!r}")
        self.assertEqual(manifest["name"], "openconcierge")
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(manifest["hermes_requires"], ">=0.12.0")

        owned = manifest.get("distribution_owned", [])
        self.assertIsInstance(owned, list, "distribution_owned must be a list")
        for path in ("distribution.yaml", "SOUL.md", "skills/openconcierge/"):
            self.assertIn(path, owned, f"distribution_owned must declare {path!r}")

        for forbidden in ("config.yaml", ".env", "auth.json", "mcp.json", "cron/"):
            self.assertNotIn(forbidden, owned, f"distribution_owned must not declare {forbidden!r}")

        soul_path = ROOT / "SOUL.md"
        self.assertTrue(soul_path.is_file(), "SOUL.md must exist")
        self.assertGreater(len(soul_path.read_text(encoding="utf-8").strip()), 0, "SOUL.md must not be empty")

        for path in ("distribution.yaml", "SOUL.md", "skills/openconcierge/"):
            self.assertTrue((ROOT / path).exists(), f"owned path {path!r} must exist on disk")

    def test_soul_md_safety_commitments(self):
        soul_path = ROOT / "SOUL.md"
        self.assertTrue(soul_path.is_file(), "SOUL.md must exist")
        body = soul_path.read_text(encoding="utf-8")

        required_phrases = (
            "Never invent products, prices, availability, ratings, specifications, or source claims.",
            "Do not pressure the user, transact, reserve inventory, or claim that a volatile price or stock status is permanent.",
            "Use the active Hermes search capabilities rather than requesting a particular provider.",
            "Store stable shopping preferences only after the user confirms them, and do not persist sensitive constraints unless explicitly requested.",
        )

        missing = [phrase for phrase in required_phrases if phrase not in body]
        self.assertEqual(missing, [], f"SOUL.md is missing safety commitments: {missing}")


if __name__ == "__main__":
    unittest.main()
