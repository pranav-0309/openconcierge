from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "bootstrap" / "build-release-manifest.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "build_release_manifest", SCRIPT
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildManifestValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()

    def test_accepts_https_distribution_and_skill_sources(self):
        manifest = self.module.build_manifest(
            "https://example.com/openconcierge/dist.tar.gz",
            "https://example.com/skills/openconcierge/SKILL.md",
            "1.2.3",
        )
        self.assertEqual(
            manifest,
            {
                "distribution_source": "https://example.com/openconcierge/dist.tar.gz",
                "skill_source": "https://example.com/skills/openconcierge/SKILL.md",
                "version": "1.2.3",
            },
        )

    def test_accepts_local_absolute_distribution_path(self):
        local_path = str((ROOT / "bootstrap").resolve())
        manifest = self.module.build_manifest(
            local_path, "openconcierge", "0.1.0"
        )
        self.assertEqual(manifest["distribution_source"], local_path)
        self.assertEqual(manifest["skill_source"], "openconcierge")
        self.assertEqual(manifest["version"], "0.1.0")

    def test_rejects_empty_sources(self):
        with self.assertRaises(ValueError):
            self.module.build_manifest("", "openconcierge", "0.1.0")
        with self.assertRaises(ValueError):
            self.module.build_manifest("https://example.com/dist", "", "0.1.0")

    def test_rejects_http_sources_for_production(self):
        with self.assertRaises(ValueError):
            self.module.build_manifest(
                "http://example.com/dist", "openconcierge", "0.1.0"
            )
        with self.assertRaises(ValueError):
            self.module.build_manifest(
                "https://example.com/dist",
                "http://example.com/skills/openconcierge/SKILL.md",
                "0.1.0",
            )

    def test_rejects_non_semantic_version(self):
        bad_versions = [
            "",
            "1",
            "1.2",
            "1.2.3.4",
            "v1.2.3",
            "1.2.3-rc1",
            "abc",
            "0.1.0 ",
            " 0.1.0",
        ]
        for bad in bad_versions:
            with self.subTest(version=bad):
                with self.assertRaises(ValueError):
                    self.module.build_manifest(
                        "https://example.com/dist",
                        "openconcierge",
                        bad,
                    )

    def test_does_not_emit_secrets(self):
        manifest = self.module.build_manifest(
            "https://example.com/dist",
            "openconcierge",
            "0.1.0",
        )
        self.assertEqual(
            set(manifest.keys()),
            {"distribution_source", "skill_source", "version"},
        )
        self.assertEqual(
            manifest["distribution_source"], "https://example.com/dist"
        )
        self.assertEqual(manifest["skill_source"], "openconcierge")
        self.assertEqual(manifest["version"], "0.1.0")
        for value in manifest.values():
            self.assertNotIn("OPENAI_API_KEY", value)
            self.assertNotIn("TAVILY_API_KEY", value)


class BuildManifestCliTests(unittest.TestCase):
    def _run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_atomic_write_does_not_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "release.json"
            first = self._run_cli(
                "--distribution-source",
                "./",
                "--skill-source",
                "openconcierge",
                "--version",
                "0.1.0",
                "--output",
                str(output),
            )
            self.assertEqual(
                first.returncode,
                0,
                msg=f"stdout={first.stdout!r} stderr={first.stderr!r}",
            )
            self.assertTrue(output.is_file())
            self.assertFalse((output.parent / "release.json.tmp").exists())
            original = output.read_text(encoding="utf-8")
            original_data = json.loads(original)
            self.assertEqual(original_data["version"], "0.1.0")

            second = self._run_cli(
                "--distribution-source",
                "./",
                "--skill-source",
                "openconcierge",
                "--version",
                "0.2.0",
                "--output",
                str(output),
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), original)
            self.assertFalse((output.parent / "release.json.tmp").exists())

    def test_atomic_write_with_force_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "release.json"
            first = self._run_cli(
                "--distribution-source",
                "./",
                "--skill-source",
                "openconcierge",
                "--version",
                "0.1.0",
                "--output",
                str(output),
            )
            self.assertEqual(
                first.returncode,
                0,
                msg=f"stdout={first.stdout!r} stderr={first.stderr!r}",
            )

            second = self._run_cli(
                "--distribution-source",
                "./",
                "--skill-source",
                "openconcierge",
                "--version",
                "0.2.0",
                "--output",
                str(output),
                "--force",
            )
            self.assertEqual(
                second.returncode,
                0,
                msg=f"stdout={second.stdout!r} stderr={second.stderr!r}",
            )
            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], "0.2.0")
            self.assertFalse((output.parent / "release.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()