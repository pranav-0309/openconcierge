from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALL_PS1 = ROOT / "bootstrap" / "install.ps1"
FAKE_HERMES = ROOT / "tests" / "installer" / "fake_hermes.py"
PWSH = shutil.which("pwsh")


@unittest.skipIf(PWSH is None, "PowerShell 7 is required to exercise the Windows installer.")
class PowerShellInstallerBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="oc-ps-install-"))
        self.bin_dir = self.tmp / "bin"
        self.bin_dir.mkdir()
        self.source_dir = self.tmp / "src"
        self.source_dir.mkdir()
        for name in ("distribution.yaml", "SOUL.md"):
            src = ROOT / name
            if src.exists():
                shutil.copy2(src, self.source_dir / name)
        skills_dst = self.source_dir / "skills" / "openconcierge"
        skills_dst.mkdir(parents=True)
        src_skill = ROOT / "skills" / "openconcierge" / "SKILL.md"
        if src_skill.exists():
            shutil.copy2(src_skill, skills_dst / "SKILL.md")
        fake_path = str(FAKE_HERMES.resolve())
        wrapper = self.bin_dir / "hermes.cmd"
        wrapper.write_text(
            "@echo off\r\n"
            f'python "{fake_path}" %*\r\n',
            encoding="utf-8",
        )
        self.state_path = self.tmp / "fake_hermes_state.json"
        self.state_path.write_text(json.dumps({}), encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _read_state(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _set_state(self, **kwargs) -> None:
        state: dict = {}
        if self.state_path.exists():
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        state.update(kwargs)
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

    def _run(self, *args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["FAKE_HERMES_STATE"] = str(self.state_path)
        env["HERMES_BIN"] = str(self.bin_dir / "hermes.cmd")
        env["PATH"] = str(self.bin_dir) + os.pathsep + env.get("PATH", "")
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(INSTALL_PS1), *args],
            env=env,
            capture_output=True,
            text=True,
        )


class DedicatedModeTests(PowerShellInstallerBase):
    def test_dedicated_mode_installs_distribution(self) -> None:
        result = self._run(
            "-Source", str(self.source_dir),
            "-Mode", "dedicated",
            "-Profile", "openconcierge",
            "-Yes",
            "-NoDesktop",
        )
        state = self._read_state()
        self.assertEqual(
            result.returncode, 0,
            msg=f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}",
        )
        self.assertTrue(state.get("distribution_installed"))
        self.assertTrue(state.get("profile_created"))
        self.assertFalse(state.get("desktop_launched", False))
        self.assertIn(["doctor"], state["calls"])

    def test_no_desktop_skips_desktop(self) -> None:
        result = self._run(
            "-Source", str(self.source_dir),
            "-Mode", "dedicated",
            "-Profile", "openconcierge",
            "-Yes",
            "-NoDesktop",
        )
        state = self._read_state()
        self.assertEqual(
            result.returncode, 0,
            msg=f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}",
        )
        self.assertFalse(state.get("desktop_launched", False))

    def test_repair_with_yes_calls_update(self) -> None:
        self._set_state(profile_create_exit=1)
        result = self._run(
            "-Source", str(self.source_dir),
            "-Mode", "dedicated",
            "-Profile", "openconcierge",
            "-Repair",
            "-Yes",
            "-NoDesktop",
        )
        state = self._read_state()
        self.assertEqual(
            result.returncode, 0,
            msg=f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}",
        )
        self.assertTrue(state.get("profile_updated"))
        install_calls = [
            call for call in state.get("calls", [])
            if len(call) >= 2 and call[0] == "profile" and call[1] == "install"
        ]
        self.assertEqual(install_calls, [])

    def test_search_capability_match_is_case_insensitive(self) -> None:
        self._set_state(tools_output="WEB ENABLED\nMCP_CUSTOM_SEARCH_SEARCH ENABLED")
        result = self._run(
            "-Source", str(self.source_dir),
            "-Mode", "dedicated",
            "-Profile", "openconcierge",
            "-Yes",
            "-NoDesktop",
        )
        self.assertEqual(
            result.returncode, 0,
            msg=f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}",
        )
        combined = (result.stdout + result.stderr).lower()
        self.assertNotIn("no compatible web search tool", combined)


class ExistingModeTests(PowerShellInstallerBase):
    def test_existing_mode_installs_skill(self) -> None:
        result = self._run(
            "-Source", str(self.source_dir),
            "-SkillSource", "openconcierge",
            "-Mode", "existing",
            "-Profile", "openconcierge",
            "-Yes",
            "-NoDesktop",
        )
        state = self._read_state()
        self.assertEqual(
            result.returncode, 0,
            msg=f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}",
        )
        self.assertTrue(state.get("skill_installed"))
        self.assertFalse(state.get("profile_created", False))
        self.assertFalse(state.get("distribution_installed", False))


class ChannelTests(PowerShellInstallerBase):
    def test_channel_telegram_does_not_start_gateway(self) -> None:
        result = self._run(
            "-Source", str(self.source_dir),
            "-Mode", "dedicated",
            "-Profile", "openconcierge",
            "-Channel", "telegram",
            "-Yes",
            "-NoDesktop",
        )
        state = self._read_state()
        self.assertEqual(
            result.returncode, 0,
            msg=f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}",
        )
        combined = (result.stdout + result.stderr).lower()
        self.assertIn("telegram", combined)
        for call in state.get("calls", []):
            joined = " ".join(str(part) for part in call).lower()
            self.assertNotIn("gateway", joined)
        self.assertTrue(state.get("distribution_installed"))


class FailureModeTests(PowerShellInstallerBase):
    def test_doctor_failure_returns_three(self) -> None:
        self._set_state(doctor_exit=1)
        result = self._run(
            "-Source", str(self.source_dir),
            "-Mode", "dedicated",
            "-Profile", "openconcierge",
            "-Yes",
            "-NoDesktop",
        )
        state = self._read_state()
        self.assertEqual(result.returncode, 3)
        self.assertFalse(state.get("distribution_installed", False))
        self.assertFalse(state.get("profile_created", False))
        self.assertFalse(state.get("skill_installed", False))


class SecretSafetyTests(PowerShellInstallerBase):
    def test_secret_in_environment_does_not_appear_in_output(self) -> None:
        result = self._run(
            "-Source", str(self.source_dir),
            "-Mode", "dedicated",
            "-Profile", "openconcierge",
            "-Yes",
            "-NoDesktop",
            extra_env={
                "OPENAI_API_KEY": "secret-openai-value",
                "TAVILY_API_KEY": "secret-tavily-value",
            },
        )
        self.assertNotIn("secret-openai-value", result.stdout)
        self.assertNotIn("secret-openai-value", result.stderr)
        self.assertNotIn("secret-tavily-value", result.stdout)
        self.assertNotIn("secret-tavily-value", result.stderr)


class SourceResolutionTests(PowerShellInstallerBase):
    def test_manifest_distribution_source_is_used_when_no_source_argument(self) -> None:
        bootstrap_dir = self.tmp / "bootstrap"
        bootstrap_dir.mkdir()
        shutil.copy2(INSTALL_PS1, bootstrap_dir / "install.ps1")
        for name in ("distribution.yaml", "SOUL.md"):
            src = ROOT / name
            if src.exists():
                shutil.copy2(src, bootstrap_dir / name)
        skills_dst = bootstrap_dir / "skills" / "openconcierge"
        skills_dst.mkdir(parents=True)
        src_skill = ROOT / "skills" / "openconcierge" / "SKILL.md"
        if src_skill.exists():
            shutil.copy2(src_skill, skills_dst / "SKILL.md")
        manifest_path = bootstrap_dir / "release.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "distribution_source": "./",
                    "skill_source": "openconcierge",
                    "version": "0.1.0",
                }
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["FAKE_HERMES_STATE"] = str(self.state_path)
        env["HERMES_BIN"] = str(self.bin_dir / "hermes.cmd")
        env["PATH"] = str(self.bin_dir) + os.pathsep + env.get("PATH", "")
        result = subprocess.run(
            [
                PWSH,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(bootstrap_dir / "install.ps1"),
                "-Mode",
                "dedicated",
                "-Yes",
                "-NoDesktop",
            ],
            env=env,
            capture_output=True,
            text=True,
        )

        state = self._read_state()
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}",
        )
        install_calls = [
            call
            for call in state.get("calls", [])
            if len(call) >= 2 and call[0] == "profile" and call[1] == "install"
        ]
        self.assertEqual(len(install_calls), 1, msg=f"calls: {state.get('calls')}")
        self.assertEqual(
            str(Path(install_calls[0][2]).resolve()),
            str(bootstrap_dir.resolve()),
        )
        self.assertTrue(state.get("distribution_installed"))


if __name__ == "__main__":
    unittest.main()
