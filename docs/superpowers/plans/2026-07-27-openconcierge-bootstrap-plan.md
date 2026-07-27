# OpenConcierge Cross-Platform Bootstrapper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide one guided Windows/macOS/Linux setup flow that installs official Hermes when necessary, offers dedicated-profile or existing-profile skill mode, and passively validates the OpenConcierge installation without making model or search calls.

**Architecture:** Two thin entry points, `install.sh` and `install.ps1`, implement the same explicit state machine and invoke only supported Hermes commands. They resolve a local source or generated release manifest, delegate missing-Hermes installation to official Nous Research installers, and never contain shopping or ranking logic. A Python subprocess harness tests both scripts against a fake Hermes executable.

**Tech Stack:** Bash, PowerShell, Python 3.11 standard library test harness, Hermes CLI/Desktop commands, HTTPS downloads from official Hermes installer endpoints.

---

## Scope and dependency

Run this plan only after `docs/superpowers/plans/2026-07-27-openconcierge-core-distribution-plan.md` is complete and its unit tests pass. The bootstrapper installs artifacts; it does not edit `SOUL.md`, implement search selection, score products, or store memory.

The current workspace is not a Git checkout. Do not create commits during implementation unless the user explicitly requests them.

## File ownership map

Create these files:

- `bootstrap/install.sh`: macOS/Linux guided entry point.
- `bootstrap/install.ps1`: Windows guided entry point.
- `bootstrap/release-manifest.schema.json`: schema for release-generated source metadata.
- `bootstrap/build-release-manifest.py`: release-only generator for source metadata.
- `tests/installer/fake_hermes.py`: deterministic fake Hermes CLI used by both script tests.
- `tests/installer/test_shell_installer.py`: Bash flow tests.
- `tests/installer/test_powershell_installer.py`: PowerShell flow tests.
- `tests/installer/test_release_manifest.py`: source-resolution and manifest-validation tests.
- `tests/installer/test_build_release_manifest.py`: release metadata generator tests.
- `tests/installer/fixtures/release.json`: local test manifest with temporary file/HTTP sources.

Do not create a GUI, Electron app, background daemon, MCP server, or a second updater.

## Installer contract

Both entry points accept the same logical options. The examples below use a local checkout and the published skill identifier:

```text
--source ./
--skill-source openconcierge
--source-profile default
--profile openconcierge
--mode interactive|dedicated|existing
--channel desktop|telegram
--repair
--yes
--no-desktop
```

PowerShell uses the equivalent named parameters:

```text
-Source .\
-SkillSource openconcierge
-SourceProfile default
-Profile openconcierge
-Mode interactive|dedicated|existing
-Channel desktop|telegram
-Repair
-Yes
-NoDesktop
```

Defaults:

- `mode`: `interactive`
- `profile`: `openconcierge`
- `source-profile`: `default` when noninteractive mode is used; interactive mode displays the available profiles and asks the user to select one
- `channel`: `desktop` when `--yes` is used; interactive mode asks whether to configure Desktop only or a separate Telegram bot
- `repair`: false
- `source`: repository root when the script is inside a checkout; otherwise `distribution_source` in the adjacent release manifest
- `skill-source`: `skill_source` in the adjacent release manifest
- `--yes`: false
- `--no-desktop`: false

Exit codes are stable:

- `0`: installation and passive validation succeeded; a missing search capability may produce a warning but does not fail installation.
- `2`: user cancelled or chose to finish Hermes setup manually.
- `3`: Hermes installation, profile, or skill command failed.
- `4`: passive validation found that the requested profile or artifact is not registered.

## Task 1: Create manifest validation and fake-Hermes test seams

**Files:**
- Create: `bootstrap/release-manifest.schema.json`
- Create: `tests/installer/__init__.py`
- Create: `tests/installer/fixtures/release.json`
- Create: `tests/installer/fake_hermes.py`
- Create: `tests/installer/test_release_manifest.py`

- [ ] **Step 1: Define the release manifest schema and package marker**

Create `tests/installer/__init__.py` as an empty file so the directory is a test package.

Create `bootstrap/release-manifest.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["distribution_source", "skill_source"],
  "properties": {
    "distribution_source": {
      "type": "string",
      "minLength": 1
    },
    "skill_source": {
      "type": "string",
      "minLength": 1
    },
    "version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"
    }
  }
}
```

The schema is documentation and a validation contract; runtime validation must use Python's standard library and enforce the same required fields without adding a JSON-schema dependency.

- [ ] **Step 2: Create a non-networking local fixture**

Create `tests/installer/fixtures/release.json` with paths relative to the fixture directory:

```json
{
  "distribution_source": "../../..",
  "skill_source": "http://127.0.0.1:8765/skills/openconcierge/SKILL.md",
  "version": "0.1.0"
}
```

The test resolver must resolve the distribution path to an absolute path and must never fetch it. The HTTP skill URL is used only by a test that starts a local standard-library server.

- [ ] **Step 3: Implement the fake Hermes command**

Create `tests/installer/fake_hermes.py` with this behavior:

```python
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

state_path = Path(os.environ["FAKE_HERMES_STATE"])
state = json.loads(state_path.read_text(encoding="utf-8"))
raw_args = sys.argv[1:]
state.setdefault("calls", []).append(raw_args)

args = list(raw_args)
if len(args) >= 2 and args[0] in {"-p", "--profile"}:
    state["last_profile"] = args[1]
    args = args[2:]

if args[:1] == ["doctor"]:
    print("Hermes doctor: healthy")
elif args[:2] == ["profile", "show"] or args[:1] == ["profile"]:
    print("Profile: openconcierge\nGateway: stopped\nSkills: openconcierge")
elif args[:2] == ["skills", "list"]:
    print("openconcierge")
elif args[:2] == ["tools", "list"]:
    print("web enabled\nmcp_custom_search_search enabled")
elif args[:2] == ["profile", "create"]:
    state["profile_created"] = True
    print("Profile created")
elif args[:2] == ["profile", "install"]:
    state["distribution_installed"] = True
    print("Distribution installed")
elif args[:2] == ["skills", "install"]:
    state["skill_installed"] = True
    print("Skill installed")
elif args[:2] == ["profile", "update"]:
    state["profile_updated"] = True
    print("Profile updated")
elif args[:2] == ["profile", "list"]:
    print("default\ncoder\nopenconcierge")
elif args[:1] == ["desktop"]:
    state["desktop_launched"] = True
    print("Desktop launched")
else:
    print("unsupported fake Hermes command", file=sys.stderr)
    state["unsupported"] = args
    state_path.write_text(json.dumps(state), encoding="utf-8")
    raise SystemExit(3)

state_path.write_text(json.dumps(state), encoding="utf-8")
```

The real scripts must support `HERMES_BIN` as a test-only command override. In normal use, resolve `hermes` from `PATH`; in tests, execute the fake script with the current Python interpreter.

- [ ] **Step 4: Write manifest resolver tests**

Create `tests/installer/test_release_manifest.py` with these assertions:

```python
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
```

- [ ] **Step 5: Run the new tests before writing the scripts**

Run:

```text
python -m unittest tests.installer.test_release_manifest -v
```

Expected: PASS for the resolver contract. No external URL is contacted.

## Task 2: Implement the POSIX bootstrapper with TDD seams

**Files:**
- Create: `bootstrap/install.sh`
- Create: `tests/installer/test_shell_installer.py`
- Modify: `tests/installer/fake_hermes.py`

- [ ] **Step 1: Write the shell-flow tests first**

Create `tests/installer/test_shell_installer.py` using `subprocess.run`. Each test creates a temporary directory, copies the repository into a local source path, prepends a fake `hermes` executable to `PATH`, and sets `FAKE_HERMES_STATE`. Invoke the script with `--source`, `--mode`, `--profile`, `--yes`, and `--no-desktop` so no prompt or GUI is opened.

The required assertions are:

```python
self.assertEqual(result.returncode, 0)
self.assertTrue(state["distribution_installed"])
self.assertFalse(state.get("desktop_launched", False))
self.assertIn(["doctor"], state["calls"])
```

Add separate tests for:

- dedicated mode calls `profile create` before `profile install`;
- existing mode calls `skills install` and never calls `profile create` or `profile install`;
- `--channel telegram` after dedicated installation prints the Telegram handoff message, never calls gateway commands, and exits `0`;
- an existing profile collision exits with `2` unless `--yes` is paired with `--repair` and the existing profile is the OpenConcierge distribution;
- a fake `doctor` failure exits with `3` and does not install an artifact;
- passive validation warns when tool output has no `web`, `search`, `mcp`, `exa`, `tavily`, `brave`, `duckduckgo`, `serp`, `firecrawl`, `searx`, `parallel`, or `xai` signal but still exits `0`;
- a secret placed in the fake environment does not appear in stdout or stderr;
- rerunning an already-installed dedicated profile with `--repair --yes` calls `profile update` and never calls `profile create` again.

- [ ] **Step 2: Implement strict shell setup and argument parsing**

Start `bootstrap/install.sh` with:

```bash
#!/usr/bin/env bash
set -euo pipefail

PROFILE="openconcierge"
MODE="interactive"
SOURCE=""
SKILL_SOURCE=""
SOURCE_PROFILE="default"
CHANNEL="desktop"
REPAIR=0
ASSUME_YES=0
NO_DESKTOP=0
HERMES_BIN="${HERMES_BIN:-hermes}"

fail() {
  printf '%s\n' "$1" >&2
  exit "${2:-3}"
}

usage() {
  printf '%s\n' 'Usage: install.sh [--source ./] [--skill-source openconcierge] [--source-profile default] [--profile openconcierge] [--mode interactive|dedicated|existing] [--channel desktop|telegram] [--repair] [--yes] [--no-desktop]'
}
```

Parse every supported option explicitly, including `--source-profile`. Reject unknown options, empty profile names, and mode values other than `interactive`, `dedicated`, or `existing` with exit code `3`. Never enable shell tracing and never print environment values.

- [ ] **Step 3: Implement source resolution**

Resolve `SOURCE` and `SKILL_SOURCE` in this order:

1. Explicit command-line argument.
2. `release.json` adjacent to the script, validated for nonempty `distribution_source` and `skill_source`.
3. Repository root one directory above `bootstrap/` when `distribution.yaml` exists there; for existing-profile mode, require an explicit skill URL or release manifest because Hermes's documented skill installer accepts a hub identifier or HTTP(S) `SKILL.md` URL.
4. Fail with a plain-language message and exit `3` if the selected mode has no source.

For a local source, require `distribution.yaml` and `skills/openconcierge/SKILL.md`. Do not download a local path.

- [ ] **Step 4: Implement Hermes detection and official installation handoff**

Add functions with these behaviors:

```bash
has_hermes() {
  command -v "$HERMES_BIN" >/dev/null 2>&1
}

check_hermes() {
  "$HERMES_BIN" doctor >/dev/null
}

install_official_hermes() {
  local installer
  installer="$(mktemp)"
  curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
    "https://hermes-agent.nousresearch.com/install.sh" \
    --output "$installer" || fail 'Could not download the official Hermes installer.' 3
  bash "$installer" || fail 'The official Hermes installer did not complete.' 3
  rm -f "$installer"
}
```

On macOS/Linux, use the official HTTPS installer above, then check that `hermes` is on `PATH`. On Windows, the PowerShell implementation uses the official `install.ps1` endpoint in its own task. Do not pipe a remote response directly into a shell. If a future official release publishes a checksum or signature, the release manifest and script must verify it before execution.

If Hermes is absent, print that the official installer will open/setup Hermes, run the handoff, re-check `hermes doctor`, and then continue. If the user declines, exit `2` without modifying an OpenConcierge profile.

- [ ] **Step 5: Implement mode selection and dedicated installation**

Interactive mode prints two plain-language choices and reads `1` or `2`. `--mode dedicated` and `--mode existing` bypass the prompt.

For dedicated mode, execute these commands in this order, substituting validated shell variables:

```bash
"$HERMES_BIN" profile create "$PROFILE" --clone-from "$SOURCE_PROFILE"
"$HERMES_BIN" profile install "$SOURCE" --name "$PROFILE" --alias --force --yes
```

`SOURCE_PROFILE` is the active configured profile selected by the user. Obtain it from `hermes profile list` output or an explicit `--source-profile` option added alongside the existing options. Never call `profile use`; the installer must not change the user's default profile.

If `profile create` reports that the target already exists, show the target profile name and require an explicit repair/update choice. Do not pass `--force` until the user has confirmed the target is the OpenConcierge profile. When `--repair` and `--yes` are both present and the existing target matches the OpenConcierge distribution, run `hermes profile update "$PROFILE" --yes` instead of `profile install`.

After installation, run:

```bash
"$HERMES_BIN" profile show "$PROFILE"
"$HERMES_BIN" -p "$PROFILE" skills list --source all --enabled-only
```

- [ ] **Step 6: Implement existing-profile skill installation**

For existing mode, validate the selected profile with `profile show`, then run exactly:

```bash
"$HERMES_BIN" -p "$PROFILE" skills install "$SKILL_SOURCE" --name openconcierge --yes
```

Do not call `profile create`, `profile install`, `profile use`, `config set`, `config edit`, or gateway commands in this mode. If the skill already exists, offer update/skip/cancel; never overwrite a different skill name without confirmation.

- [ ] **Step 7: Implement passive tool and Desktop validation**

Capture, without echoing environment values:

```bash
"$HERMES_BIN" tools list --platform cli
```

Treat output containing `web`, `search`, `mcp`, `exa`, `tavily`, `brave`, `duckduckgo`, `serp`, `firecrawl`, `searx`, `parallel`, or `xai` (case-insensitive) as a search-capability signal. If no signal exists, print a warning directing the user to Hermes Desktop tools, skills, or MCP settings and keep exit code `0`.

Unless `--no-desktop` is set, launch the selected profile through the supported command:

```bash
"$HERMES_BIN" -p "$PROFILE" desktop
```

If the selected Hermes version rejects the profile flag for Desktop, print the exact command the user can run manually and exit `3`; do not silently launch the wrong profile.

- [ ] **Step 8: Add optional Telegram channel handoff**

If `--channel telegram` is set or the interactive user picks a separate Telegram bot for the dedicated profile, print a plain-language summary that Hermes must be opened to `Gateway → Telegram` so the user can create a new bot token for the new profile. Then exit with code `0`; do not start a gateway from the installer. The installer never copies an active gateway token from another profile.

- [ ] **Step 9: Run shell tests and syntax checks**

Run:

```text
python -m unittest tests.installer.test_shell_installer -v
bash -n bootstrap/install.sh
```

Expected: all shell-flow tests pass and `bash -n` exits `0`.

## Task 3: Implement the Windows PowerShell bootstrapper with parity tests

**Files:**
- Create: `bootstrap/install.ps1`
- Create: `tests/installer/test_powershell_installer.py`
- Modify: `tests/installer/fake_hermes.py`

- [ ] **Step 1: Write the PowerShell parity tests first**

Create `tests/installer/test_powershell_installer.py` that invokes:

```text
pwsh -NoProfile -ExecutionPolicy Bypass -File bootstrap/install.ps1 -Source $SOURCE -Mode dedicated -Profile openconcierge -Yes -NoDesktop
```

Use the same fake-Hermes state file and assertions as the shell tests. Add tests for existing mode, doctor failure, secret redaction, source validation, idempotent collision handling, and missing-search warning. Skip the test only when `pwsh` is unavailable; record that the Windows suite must run on a Windows CI worker.

- [ ] **Step 2: Implement PowerShell parameter validation**

Begin `bootstrap/install.ps1` with:

```powershell
[CmdletBinding()]
param(
    [string]$Source = "",
    [string]$SkillSource = "",
    [string]$SourceProfile = "default",
    [string]$Profile = "openconcierge",
    [ValidateSet("interactive", "dedicated", "existing")]
    [string]$Mode = "interactive",
    [ValidateSet("desktop", "telegram")]
    [string]$Channel = "desktop",
    [switch]$Repair,
    [switch]$Yes,
    [switch]$NoDesktop
)

$ErrorActionPreference = "Stop"
$HermesBin = if ($env:HERMES_BIN) { $env:HERMES_BIN } else { "hermes" }

function Stop-Setup([string]$Message, [int]$Code = 3) {
    [Console]::Error.WriteLine($Message)
    exit $Code
}
```

Reject an empty profile or unknown option before any external command runs. Do not print `$env:*` values or enable transcript logging.

- [ ] **Step 3: Implement official Windows Hermes handoff**

Download the official script to a temporary file before executing it:

```powershell
function Install-OfficialHermes {
    $temporary = Join-Path $env:TEMP ("hermes-install-{0}.ps1" -f ([guid]::NewGuid()))
    try {
        Invoke-WebRequest -Uri "https://hermes-agent.nousresearch.com/install.ps1" -OutFile $temporary
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $temporary
        if ($LASTEXITCODE -ne 0) {
            Stop-Setup "The official Hermes installer did not complete." 3
        }
    }
    catch {
        Stop-Setup "Could not download or run the official Hermes installer." 3
    }
    finally {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }
}
```

After the handoff, run `hermes doctor`, then launch `hermes desktop` after OpenConcierge installation unless `-NoDesktop` was supplied. Do not bundle Hermes binaries.

- [ ] **Step 4: Implement the same source, mode, channel, repair, and validation state machine**

Match the shell behavior exactly:

- explicit arguments override release metadata;
- dedicated mode clones the selected source profile and runs `hermes profile install "$SOURCE" --name "$PROFILE" --alias --force --yes`;
- existing mode runs `hermes -p $PROFILE skills install $SKILL_SOURCE --name openconcierge --yes`;
- no mode changes the active default profile;
- `--channel telegram` prints a Telegram handoff message after installation and never calls gateway commands from the installer;
- `--repair` paired with `--yes` and a matching distribution source allows `hermes profile update` to refresh an existing OpenConcierge profile without prompting;
- passive checks use `profile show`, `skills list --source all --enabled-only`, and `tools list --platform cli`;
- missing search capability produces a warning and exit code `0`;
- user cancellation returns `2`;
- command failures return `3`;
- registration failures return `4`.

Use `& $HermesBin @arguments` for argument-safe invocation. Never construct a command string and pass it to `Invoke-Expression`.

- [ ] **Step 5: Run PowerShell tests and syntax checks**

Run:

```text
python -m unittest tests.installer.test_powershell_installer -v
pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('bootstrap/install.ps1',[ref]$null,[ref]$null) | Out-Null"
```

Expected: all parity tests pass and PowerShell parsing exits `0`.

## Task 4: Add release metadata generation without embedding secrets

**Files:**
- Create: `bootstrap/build-release-manifest.py`
- Create: `tests/installer/test_build_release_manifest.py`
- Modify: `bootstrap/release-manifest.schema.json`

- [ ] **Step 1: Write release-manifest generation tests**

Test a function with this API:

```python
def build_manifest(distribution_source: str, skill_source: str, version: str) -> dict[str, str]:
    """Validate and return release metadata for the bootstrap scripts."""
```

Assert that it:

- accepts nonempty HTTPS distribution and skill sources;
- accepts a local absolute distribution path for development;
- rejects empty sources;
- rejects `http://` for production source values;
- accepts only semantic versions such as `0.1.0`;
- writes no credentials, environment values, or user paths other than an explicitly supplied local development path.

- [ ] **Step 2: Implement the manifest builder**

Use only `argparse`, `json`, `pathlib`, `re`, and `urllib.parse`. The CLI must be:

```text
python bootstrap/build-release-manifest.py --distribution-source ./ --skill-source openconcierge --version 0.1.0 --output bootstrap/release.json
```

The output must be JSON with exactly `distribution_source`, `skill_source`, and `version`. Write through a temporary file and replace the destination atomically. Refuse to overwrite an existing manifest unless `--force` is supplied.

The public release job supplies the repository's actual published distribution and skill sources when it generates `release.json`; local development runs the script with a local source and the published skill identifier `openconcierge`. This keeps source hosting out of runtime logic without inventing a repository URL in source code.

- [ ] **Step 3: Add release manifest loading to both scripts**

When no explicit source arguments are present, both scripts read `bootstrap/release.json`, validate the required string fields, and use its values. A malformed or absent release manifest produces a plain-language error and exit code `3` unless the script is running from a checkout with a local `distribution.yaml` and the selected mode does not need a remote skill source.

- [ ] **Step 4: Run release-manifest tests**

Run:

```text
python -m unittest tests.installer.test_build_release_manifest tests.installer.test_release_manifest -v
```

Expected: PASS, with no network access and no secret values in generated JSON.

## Task 5: Test missing-Hermes handoff and security behavior

**Files:**
- Modify: `tests/installer/test_shell_installer.py`
- Modify: `tests/installer/test_powershell_installer.py`
- Modify: `bootstrap/install.sh`
- Modify: `bootstrap/install.ps1`

- [ ] **Step 1: Test the missing-Hermes branch without contacting the internet**

Place fake `curl`, `bash`, `Invoke-WebRequest`, and `powershell.exe` commands ahead of the real commands in the test process. The fake download commands write a local official-installer fixture that creates the fake Hermes executable and exits `0`.

Assert:

- the official endpoint string is the expected HTTPS Hermes endpoint;
- the downloaded file is executed from a temporary path;
- the temporary path is removed after execution;
- a failed official installer returns `3`;
- a user cancellation before handoff returns `2`;
- no OpenConcierge profile command runs before Hermes is available.

- [ ] **Step 2: Test secret redaction**

Set `OPENAI_API_KEY`, `TAVILY_API_KEY`, and a fake gateway token in the test environment. Run both scripts with fake Hermes output that contains normal tool/profile status. Assert none of the secret values occurs in stdout, stderr, or state logs. Do not print the values in assertion failure messages.

- [ ] **Step 3: Test idempotence, profile isolation, and repair**

Run dedicated mode twice against the same fake state. The first run creates the profile. The second run with `--repair --yes` must call `profile update` and not `profile create`. The second run without `--repair` must stop for explicit confirmation. Run existing mode against a profile and assert no `profile create`, `profile install`, `profile use`, `config set`, or gateway command appears in the fake call log.

- [ ] **Step 4: Run all installer tests**

Run:

```text
python -m unittest discover -s tests/installer -v
```

Expected: all available platform tests pass; missing platform tooling is reported as an environment limitation, not silently treated as passing.

## Task 6: End-to-end passive acceptance

- [ ] **Step 1: Run static checks**

Run:

```text
bash -n bootstrap/install.sh
pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('bootstrap/install.ps1',[ref]$null,[ref]$null) | Out-Null"
python -m py_compile bootstrap/build-release-manifest.py tests/installer/fake_hermes.py
```

Expected: all commands exit `0`.

- [ ] **Step 2: Run the complete repository suite**

Run:

```text
python -m unittest discover -s tests -v
```

Expected: core distribution, ranking, skill, safety, manifest, shell, and PowerShell tests pass. No test sends an LLM prompt, performs a web search, launches a real gateway, or uses a real credential.

- [ ] **Step 3: Execute a local dedicated dry run**

With Hermes installed and a temporary `HERMES_HOME`, run:

```text
bash bootstrap/install.sh --source "$PWD" --mode dedicated --profile openconcierge-test --yes --no-desktop
```

Expected: the profile is created and registered; passive checks run; no model or search request occurs.

- [ ] **Step 4: Execute a local existing-profile dry run**

Run the same script with an existing temporary Hermes profile and a locally served `SKILL.md` source:

```text
bash bootstrap/install.sh --source "$PWD" --skill-source http://127.0.0.1:8765/skills/openconcierge/SKILL.md --mode existing --profile existing-test --yes --no-desktop
```

Expected: only the skill-install command runs; the existing profile identity, settings, memory, and gateway state remain unchanged.

## Bootstrapper definition of done

- Windows, macOS, and Linux have equivalent guided entry points.
- Missing Hermes is handed to official HTTPS installers and then Desktop is launched through Hermes.
- Dedicated mode creates an isolated profile without changing the active default.
- Existing mode installs only the skill and preserves the existing profile.
- Existing search integrations are inspected/reused without requiring a named provider.
- Installation is idempotent, cancellable, secret-safe, and passive.
- No OpenConcierge desktop app, backend, MCP server, or updater exists.
