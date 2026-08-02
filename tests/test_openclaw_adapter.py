from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
OPENCLAW = ROOT / "harnesses" / "adapters" / "openclaw"
CODEX = ROOT / "harnesses" / "adapters" / "codex"
CORE = ROOT / "harnesses" / "core"


class OpenClawAdapterLayoutTests(unittest.TestCase):
    def test_required_files_exist(self):
        expected = (
            OPENCLAW / "SKILL.md",
            OPENCLAW / "README.md",
            OPENCLAW / "manifest.yaml",
            OPENCLAW / "references" / "interviewing.md",
            OPENCLAW / "references" / "memory-and-privacy.md",
            OPENCLAW / "references" / "recommendations.md",
            OPENCLAW / "references" / "research-and-evidence.md",
            OPENCLAW / "scripts" / "rank_candidates.py",
        )
        missing = [str(p.relative_to(ROOT)) for p in expected if not p.is_file()]
        self.assertEqual(missing, [], f"missing files: {missing}")

    def test_references_and_script_byte_identical_to_core(self):
        pairs = [
            ("references", "interviewing.md"),
            ("references", "memory-and-privacy.md"),
            ("references", "recommendations.md"),
            ("references", "research-and-evidence.md"),
            ("scripts", "rank_candidates.py"),
        ]
        for subdir, name in pairs:
            adapter_path = OPENCLAW / subdir / name
            core_path = CORE / subdir / name
            self.assertTrue(adapter_path.is_file(), f"missing {adapter_path}")
            self.assertTrue(core_path.is_file(), f"missing {core_path}")
            self.assertEqual(
                adapter_path.read_bytes(),
                core_path.read_bytes(),
                f"{adapter_path.relative_to(ROOT)} must be byte-identical to "
                f"{core_path.relative_to(ROOT)}",
            )


class OpenClawAdapterSkillMdTests(unittest.TestCase):
    def test_skill_md_body_matches_core_except_install_section(self):
        core_text = (CORE / "SKILL.md").read_text(encoding="utf-8")
        adapter_text = (OPENCLAW / "SKILL.md").read_text(encoding="utf-8")

        self.assertTrue(adapter_text.startswith("---\n"), "adapter SKILL.md must start with YAML frontmatter")
        self.assertRegex(adapter_text, r"(?m)^harness:\s*openclaw\s*$")

        core_body = self._strip_frontmatter(core_text)
        adapter_body = self._strip_frontmatter(adapter_text)

        self.assertTrue(
            adapter_body.startswith(core_body),
            "adapter SKILL.md body (after frontmatter) must begin with the core SKILL.md body byte-for-byte",
        )

        appended = adapter_body[len(core_body):]
        self.assertIn("## OpenClaw Installation", appended, "adapter must append a '## OpenClaw Installation' section")

    def test_skill_md_differs_from_codex_adapter_only_in_harness_and_install_section(self):
        codex_skill = CODEX / "SKILL.md"
        self.assertTrue(codex_skill.is_file(), "codex adapter SKILL.md must exist (sanity)")
        self.assertTrue((OPENCLAW / "SKILL.md").is_file(), "openclaw adapter SKILL.md must exist")

        codex_text = codex_skill.read_text(encoding="utf-8")
        openclaw_text = (OPENCLAW / "SKILL.md").read_text(encoding="utf-8")

        self.assertRegex(codex_text, r"(?m)^harness:\s*codex\s*$")
        self.assertIn("## Codex Installation", codex_text)
        self.assertRegex(openclaw_text, r"(?m)^harness:\s*openclaw\s*$")
        self.assertIn("## OpenClaw Installation", openclaw_text)

        self.assertNotIn("## Codex Installation", openclaw_text, "openclaw adapter must not contain the Codex install section")
        self.assertNotIn("## OpenClaw Installation", codex_text, "codex adapter must not contain the OpenClaw install section")

        codex_body = self._strip_frontmatter(codex_text)
        openclaw_body = self._strip_frontmatter(openclaw_text)
        openclaw_install_idx = openclaw_body.index("## OpenClaw Installation")
        codex_install_idx = codex_body.index("## Codex Installation")

        self.assertEqual(
            openclaw_body[:openclaw_install_idx],
            codex_body[:codex_install_idx],
            "the portion of the SKILL.md body BEFORE the install section must be byte-identical between codex and openclaw adapters",
        )

    @staticmethod
    def _strip_frontmatter(text):
        end = text.find("\n---\n", 4)
        if end == -1:
            raise AssertionError("missing closing '---' on YAML frontmatter")
        return text[end + 5 :]


class OpenClawAdapterManifestTests(unittest.TestCase):
    def test_manifest_yaml_parses_with_expected_fields(self):
        manifest_path = OPENCLAW / "manifest.yaml"
        self.assertTrue(manifest_path.is_file(), "manifest.yaml must exist")
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "openconcierge")
        self.assertEqual(manifest["harness"], "openclaw")
        self.assertIn("version", manifest)
        self.assertIn("description", manifest)
        self.assertIn("license", manifest)
        self.assertEqual(
            sorted(manifest["surfaces"]),
            sorted(["openclaw-workspace", "openclaw-global"]),
        )
        self.assertIn("install", manifest)
        for key in ("openclaw-workspace", "openclaw-global", "drop-in", "git"):
            self.assertIn(key, manifest["install"], f"install.{key} must be present in manifest")


class OpenClawAdapterNoInstallerTests(unittest.TestCase):
    FORBIDDEN_NEEDLES = ("install.sh", "install.ps1", "bootstrap/")

    def test_no_installer_references_in_adapter(self):
        offenders = []
        for path in OPENCLAW.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix in {".pyc"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for needle in self.FORBIDDEN_NEEDLES:
                if needle in text:
                    offenders.append(f"{path.relative_to(ROOT)}:{needle}")
        self.assertEqual(offenders, [], f"adapter must not reference: {self.FORBIDDEN_NEEDLES}")


class OpenClawAdapterPortabilityTests(unittest.TestCase):
    def test_adapter_is_self_contained_when_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "openconcierge"
            shutil.copytree(OPENCLAW, dest)
            self.assertTrue((dest / "SKILL.md").is_file())
            self.assertTrue((dest / "references" / "interviewing.md").is_file())
            self.assertTrue((dest / "scripts" / "rank_candidates.py").is_file())

            script = dest / "scripts" / "rank_candidates.py"
            self.assertEqual(subprocess.run(
                [sys.executable, str(script), "--help"],
                capture_output=True, text=True, check=False,
            ).returncode, 0, "rank_candidates.py --help must exit 0 from a copied adapter folder")


if __name__ == "__main__":
    unittest.main()
