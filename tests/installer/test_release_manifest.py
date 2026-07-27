from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load_manifest():
    path = ROOT / "tests" / "installer" / "fixtures" / "release.json"
    return json.loads(path.read_text(encoding="utf-8"))


class ReleaseManifestTests(unittest.TestCase):
    def test_fixture_has_required_nonempty_values(self):
        manifest = load_manifest()
        self.assertTrue(manifest["distribution_source"])
        self.assertTrue(manifest["skill_source"])

    def test_distribution_source_resolves_inside_repository(self):
        fixture = ROOT / "tests" / "installer" / "fixtures" / "release.json"
        source = (fixture.parent / load_manifest()["distribution_source"]).resolve()
        self.assertEqual(source, ROOT)
        self.assertTrue((source / "distribution.yaml").is_file())

    def test_missing_required_value_is_rejected(self):
        manifest = load_manifest()
        del manifest["skill_source"]
        with self.assertRaises(ValueError):
            self._validate(manifest)

    @staticmethod
    def _validate(manifest):
        if not isinstance(manifest, dict):
            raise ValueError("release manifest must be an object")
        for key in ("distribution_source", "skill_source"):
            if not isinstance(manifest.get(key), str) or not manifest[key]:
                raise ValueError(f"release manifest requires {key}")
        return manifest


if __name__ == "__main__":
    unittest.main()
