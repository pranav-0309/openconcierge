from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALL_SH = ROOT / "bootstrap" / "install.sh"
FAKE_HERMES = ROOT / "tests" / "installer" / "fake_hermes.py"


def to_bash_path(path: Path) -> str:
    """Convert a Windows path to a Git Bash /mnt/<drive>/... path."""
    abs_path = os.path.abspath(str(path))
    if len(abs_path) >= 2 and abs_path[1] == ":":
        drive = abs_path[0].lower()
        rest = abs_path[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"
    return abs_path.replace("\\", "/")


def shell_quote(value: str) -> str:
    """Quote a value for safe inclusion in a bash command line."""
    return "'" + value.replace("'", "'\"'\"'") + "'"


class ShellInstallerBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="oc-install-"))
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
        bash_fake = to_bash_path(FAKE_HERMES)
        wrapper = self.bin_dir / "hermes"
        wrapper.write_bytes(
            f"#!/usr/bin/env bash\nexec python3 {shell_quote(bash_fake)} \"$@\"\n".encode("utf-8")
        )
        wrapper.chmod(0o755)
        self.state_path = self.tmp / "fake_hermes_state.json"
        self.state_path.write_text(json.dumps({}), encoding="utf-8")
        self.runner = self.tmp / "run.sh"
        self.install_sh_bash = to_bash_path(INSTALL_SH)
        self.bin_dir_bash = to_bash_path(self.bin_dir)
        self.state_path_bash = to_bash_path(self.state_path)
        self.source_dir_bash = to_bash_path(self.source_dir)
        self.wrapper_bash = to_bash_path(wrapper)

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

    def _build_runner(self, args: list[str], extra_env: dict[str, str] | None = None) -> str:
        env_lines = [
            f"export FAKE_HERMES_STATE={shell_quote(self.state_path_bash)}",
            f"export HERMES_BIN={shell_quote(self.wrapper_bash)}",
            f"export PATH={shell_quote(self.bin_dir_bash + ':' + '/usr/bin:/bin')}",
        ]
        if extra_env:
            for k, v in extra_env.items():
                env_lines.append(f"export {k}={shell_quote(v)}")
        arg_str = " ".join(shell_quote(a) for a in args)
        return (
            "#!/usr/bin/env bash\n"
            + "\n".join(env_lines) + "\n"
            + f"bash {shell_quote(self.install_sh_bash)} {arg_str}\n"
        )

    def _run(self, *args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        bash_args = []
        for arg in args:
            if arg == str(self.source_dir):
                bash_args.append(self.source_dir_bash)
            else:
                bash_args.append(arg)
        runner_content = self._build_runner(bash_args, extra_env=extra_env)
        self.runner.write_bytes(runner_content.encode("utf-8"))
        self.runner.chmod(0o755)
        runner_bash = to_bash_path(self.runner)
        return subprocess.run(
            f"bash {shell_quote(runner_bash)}",
            shell=True,
            capture_output=True,
            text=True,
        )


class DedicatedModeTests(ShellInstallerBase):
    def test_dedicated_mode_installs_distribution(self) -> None:
        result = self._run(
            "--source", str(self.source_dir),
            "--mode", "dedicated",
            "--profile", "openconcierge",
            "--yes",
            "--no-desktop",
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
            "--source", str(self.source_dir),
            "--mode", "dedicated",
            "--profile", "openconcierge",
            "--yes",
            "--no-desktop",
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
            "--source", str(self.source_dir),
            "--mode", "dedicated",
            "--profile", "openconcierge",
            "--repair",
            "--yes",
            "--no-desktop",
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

    def test_missing_search_capability_is_warning(self) -> None:
        self._set_state(tools_output="configured: none\n")
        result = self._run(
            "--source", str(self.source_dir),
            "--mode", "dedicated",
            "--profile", "openconcierge",
            "--yes",
            "--no-desktop",
        )
        self.assertEqual(
            result.returncode, 0,
            msg=f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}",
        )
        self.assertIn("search", result.stderr.lower())

    def test_search_capability_match_is_case_insensitive(self) -> None:
        self._set_state(tools_output="WEB ENABLED\nMCP_CUSTOM_SEARCH_SEARCH ENABLED")
        result = self._run(
            "--source", str(self.source_dir),
            "--mode", "dedicated",
            "--profile", "openconcierge",
            "--yes",
            "--no-desktop",
        )
        self.assertEqual(
            result.returncode, 0,
            msg=f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}",
        )
        self.assertNotIn("no compatible web search tool", result.stderr.lower())


class ExistingModeTests(ShellInstallerBase):
    def test_existing_mode_installs_skill(self) -> None:
        result = self._run(
            "--source", str(self.source_dir),
            "--skill-source", "openconcierge",
            "--mode", "existing",
            "--profile", "openconcierge",
            "--yes",
            "--no-desktop",
        )
        state = self._read_state()
        self.assertEqual(
            result.returncode, 0,
            msg=f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}",
        )
        self.assertTrue(state.get("skill_installed"))
        self.assertFalse(state.get("profile_created", False))
        self.assertFalse(state.get("distribution_installed", False))


class FailureModeTests(ShellInstallerBase):
    def test_doctor_failure_returns_three(self) -> None:
        self._set_state(doctor_exit=1)
        result = self._run(
            "--source", str(self.source_dir),
            "--mode", "dedicated",
            "--profile", "openconcierge",
            "--yes",
            "--no-desktop",
        )
        state = self._read_state()
        self.assertEqual(result.returncode, 3)
        self.assertFalse(state.get("distribution_installed", False))
        self.assertFalse(state.get("profile_created", False))
        self.assertFalse(state.get("skill_installed", False))


class SecretSafetyTests(ShellInstallerBase):
    def test_secret_in_environment_does_not_appear_in_output(self) -> None:
        result = self._run(
            "--source", str(self.source_dir),
            "--mode", "dedicated",
            "--profile", "openconcierge",
            "--yes",
            "--no-desktop",
            extra_env={
                "OPENAI_API_KEY": "secret-openai-value",
                "TAVILY_API_KEY": "secret-tavily-value",
            },
        )
        self.assertNotIn("secret-openai-value", result.stdout)
        self.assertNotIn("secret-openai-value", result.stderr)
        self.assertNotIn("secret-tavily-value", result.stdout)
        self.assertNotIn("secret-tavily-value", result.stderr)


if __name__ == "__main__":
    unittest.main()
