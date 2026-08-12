## OpenClaw Adapter — End-to-End Testing Guide

This guide covers the **OpenClaw adapter** at `harnesses/adapters/openclaw/`. It is a thin, folder-shaped adapter that lets OpenClaw consume the OpenConcierge skill. The adapter inherits behavior content byte-identically from `harnesses/core/` and adds OpenClaw-specific frontmatter, a manifest, and a README.

Every step below maps to a real file or test in the repository. There are two halves:

- **Sections 1–9 (offline).** Static checks, manifest/skill/rank helpers, and the full pytest suite. No network, no OpenClaw runtime required.
- **Section 10 (live).** Hands-on install + conversational scenario. Requires an installed OpenClaw binary. Skip and rely on offline checks if you do not have OpenClaw installed yet.

---

### 1. Prerequisites

**Offline checks (Sections 1–9):**

- **Python 3.10+** (the repo is exercised on Python 3.12; `pyyaml` is the only third-party dependency and is already installed in the dev environment).
- A working directory at the **repository root** (`C:\Users\ACER\Documents\opencode_projects\open-concierge`). All commands below are run from there.
- **No live network is required.** Every static check reads from disk, and `scripts/rank_candidates.py` is exercised against local fixtures under `tests/fixtures/ranking/`.

**Live OpenClaw runtime (Section 10 only):**

- **OpenClaw** installed and on `PATH`. The spec points at `https://docs.openclaw.ai/cli/skills` for the install command. If you do not have OpenClaw installed yet, complete Sections 1–9 first — the entire adapter contract is covered by the static and pytest checks.

Confirm the Python environment is ready:

```powershell
python --version
python -c "import yaml; print('yaml', yaml.__version__)"
```

Sample output:

```
Python 3.12.10
yaml 6.0.2
```

---

### 2. Static Layout Check

The adapter folder must contain exactly this shape (eight files, mirroring an OpenClaw drop-in skill):

```
harnesses/adapters/openclaw/
├── README.md
├── SKILL.md
├── manifest.yaml
├── references/
│   ├── interviewing.md
│   ├── memory-and-privacy.md
│   ├── recommendations.md
│   └── research-and-evidence.md
└── scripts/
    └── rank_candidates.py
```

One-liner to confirm presence (use `Get-ChildItem -Recurse` and pipe through `Sort-Object` for a stable, alphabetical listing):

```powershell
Get-ChildItem -Recurse harnesses/adapters/openclaw/ | Where-Object { -not $_.PSIsContainer } | Sort-Object FullName | Format-Table FullName
```

Expected output (paths and order):

```
FullName
--------
C:\Users\ACER\Documents\opencode_projects\open-concierge\harnesses\adapters\openclaw\README.md
C:\Users\ACER\Documents\opencode_projects\open-concierge\harnesses\adapters\openclaw\SKILL.md
C:\Users\ACER\Documents\opencode_projects\open-concierge\harnesses\adapters\openclaw\manifest.yaml
C:\Users\ACER\Documents\opencode_projects\open-concierge\harnesses\adapters\openclaw\references\interviewing.md
C:\Users\ACER\Documents\opencode_projects\open-concierge\harnesses\adapters\openclaw\references\memory-and-privacy.md
C:\Users\ACER\Documents\opencode_projects\open-concierge\harnesses\adapters\openclaw\references\recommendations.md
C:\Users\ACER\Documents\opencode_projects\open-concierge\harnesses\adapters\openclaw\references\research-and-evidence.md
C:\Users\ACER\Documents\opencode_projects\open-concierge\harnesses\adapters\openclaw\scripts\rank_candidates.py
```

If any line is missing, stop and restore the file before continuing.

---

### 3. Manifest Contract

`harnesses/adapters/openclaw/manifest.yaml` is a real YAML file (parsed with `yaml.safe_load`), unlike the Codex adapter's hand-rolled manifest. The contract requires:

- Top-level keys: `name`, `description`, `version`, `license`, `harness`, `surfaces`, `install`.
- `harness: openclaw`.
- `surfaces` must equal `["openclaw-workspace", "openclaw-global"]` (order irrelevant).
- `install` must contain **all four** keys: `openclaw-workspace`, `openclaw-global`, `drop-in`, `git`.

Print the required fields and confirm they line up:

```powershell
python -c "import yaml; m = yaml.safe_load(open('harnesses/adapters/openclaw/manifest.yaml', encoding='utf-8')); print('harness:', m['harness']); print('surfaces:', m['surfaces']); print('install keys:', sorted(m['install'].keys()))"
```

Sample output:

```
harness: openclaw
surfaces: ['openclaw-workspace', 'openclaw-global']
install keys: ['drop-in', 'git', 'openclaw-global', 'openclaw-workspace']
```

What to look for:

- `harness: openclaw` — the adapter is wired to OpenClaw, not Codex/Claude/Hermes.
- `surfaces` lists exactly the two OpenClaw scopes.
- `install` has the four keys in any order; the keys map 1:1 to the four `### Install` subsections in the README.

---

### 4. SKILL.md Contract

The adapter's `SKILL.md` is the core `SKILL.md` with two OpenClaw-specific additions:

1. A YAML frontmatter that starts with `---\n` and includes `harness: openclaw`.
2. An appended `## OpenClaw Installation` section at the bottom.

Confirm the frontmatter is present and the harness line is correct:

```powershell
Get-Content harnesses/adapters/openclaw/SKILL.md -TotalCount 7
```

Sample output:

```
---
name: openconcierge
description: Research and compare products through a focused, source-backed shopping conversation.
version: 0.1.0
license: MIT
harness: openclaw
---
```

Next, confirm the body (after the closing `---`) starts with the core body byte-for-byte and the install section is appended. This is what `OpenClawAdapterSkillMdTests::test_skill_md_body_matches_core_except_install_section` enforces:

```powershell
python -c @'
from pathlib import Path
import re

core = Path("harnesses/core/SKILL.md").read_text(encoding="utf-8")
adapter = Path("harnesses/adapters/openclaw/SKILL.md").read_text(encoding="utf-8")

def body(t):
    end = t.find("\n---\n", 4)
    return t[end + 5:]

core_body = body(core)
adapter_body = body(adapter)
prefix = adapter_body[: len(core_body)]
suffix = adapter_body[len(core_body):]

print("frontmatter starts with ---:", adapter.startswith("---\n"))
print("harness: openclaw line present:", "\nharness: openclaw" in adapter[: adapter.find("\n---", 4)])
print("body starts with core body:", prefix == core_body)
print("appended tail:", repr(suffix[:60]))
print("OpenClaw install section present:", "## OpenClaw Installation" in suffix)
print("Codex install section absent:", "## Codex Installation" not in adapter)
'@
```

Sample output (the trailing `None` is a benign artifact of the heredoc end-of-line):

```
frontmatter starts with ---: True
harness: openclaw line present: True
body starts with core body: True
appended tail: '\n## OpenClaw Installation\n\nThis skill works on OpenClaw (CLI sur...'
OpenClaw install section present: True
Codex install section absent: True
```

A `False` on any line means the adapter SKILL.md has drifted — re-run the construction script from `docs/superpowers/plans/2026-08-02-openconcierge-openclaw-adapter-plan.md` Task 6.

---

### 5. Reference Byte-Identity vs Core

The four reference files in `harnesses/adapters/openclaw/references/` and `scripts/rank_candidates.py` MUST be byte-identical to the same paths under `harnesses/core/`. This is what `OpenClawAdapterLayoutTests::test_references_and_script_byte_identical_to_core` enforces.

References (use `Compare-Object` per file, then a script loop for the lot):

```powershell
$files = @("interviewing.md", "memory-and-privacy.md", "recommendations.md", "research-and-evidence.md")
$anyDiff = $false
foreach ($f in $files) {
  $core = Get-Content "harnesses/core/references/$f"
  $adapter = Get-Content "harnesses/adapters/openclaw/references/$f"
  $diff = Compare-Object -ReferenceObject $core -DifferenceObject $adapter
  if ($diff) { Write-Error "$f differs from core"; $anyDiff = $true }
}
if (-not $anyDiff) { Write-Output "OK: all four reference files are byte-identical" }
```

Expected output:

```
OK: all four reference files are byte-identical
```

Script (`fc /b` via `cmd /c` — PowerShell's `fc` is a different alias, so we route through `cmd` for a true binary compare):

```powershell
cmd /c "fc /b `"harnesses\core\scripts\rank_candidates.py`" `"harnesses\adapters\openclaw\scripts\rank_candidates.py`""
```

Expected output:

```
Comparing files HARNESSES\CORE\SCRIPTS\rank_candidates.py and HARNESSES\ADAPTERS\OPENCLAW\SCRIPTS\RANK_CANDIDATES.PY
FC: no differences encountered
```

Any line that says `***` or `****` indicates a differing byte — re-copy the file from `harnesses/core/` before continuing.

---

### 6. No-Installer-Needle Rule

The adapter MUST NOT contain `install.sh`, `install.ps1`, or `bootstrap/` anywhere (the spec explicitly says OpenClaw has no installer and uses OpenClaw's own `openclaw skills install` CLI). This is what `OpenClawAdapterNoInstallerTests::test_no_installer_references_in_adapter` enforces.

```powershell
$results = Select-String -Path "harnesses/adapters/openclaw/*","harnesses/adapters/openclaw/*/*" -Pattern "install\.(sh|ps1)|bootstrap/"
if ($results) { $results | Format-List; Write-Error "forbidden installer references found" } else { Write-Output "OK: no installer references" }
```

Expected output:

```
OK: no installer references
```

If a hit is reported, treat it as a regression — the spec is clear that the adapter is installer-free.

---

### 7. Deterministic Ranking Helper

`scripts/rank_candidates.py` is the adapter's only executable. It is stdlib-only and dependency-free. Run `--help` first, then exercise each of the three fixtures under `tests/fixtures/ranking/`.

```powershell
python harnesses/adapters/openclaw/scripts/rank_candidates.py --help
```

Expected output (exit 0):

```
usage: rank_candidates.py [-h] [--input INPUT]

options:
  -h, --help     show this help message and exit
  --input INPUT
```

Now run each fixture over stdin. Each call must exit 0:

```powershell
Get-Content tests/fixtures/ranking/basic.json | python harnesses/adapters/openclaw/scripts/rank_candidates.py
```

Expected (truncated): `"ranked": [ ... "Valid Cooling Pillow" ... ]` with `fit_score: 0.8`, plus `"rejected": [...]` lists for the over-budget and region-unavailable candidates.

```powershell
Get-Content tests/fixtures/ranking/ties.json | python harnesses/adapters/openclaw/scripts/rank_candidates.py
```

Expected (truncated): `"ranked": [ ... "Alpha Product" ... ]` first, because the tie-breaker is case-insensitive name (`Alpha Product` < `Beta Product`).

```powershell
Get-Content tests/fixtures/ranking/unknown-evidence.json | python harnesses/adapters/openclaw/scripts/rank_candidates.py
```

Expected:

```
{
  "ranked": [],
  "rejected": [],
  "unranked": [
    {
      "name": "Unverified Pillow",
      "product_url": "https://example.test/unverified",
      "reason": "unverified_must_have"
    }
  ]
}
```

Each exit code must be `0`. If `rank_candidates.py` ever exits `2`, the helper rejected the payload — that means a fixture drifted or the script changed.

---

### 8. Portability Check (Copy to Temp, Re-Run)

`OpenClawAdapterPortabilityTests::test_adapter_is_self_contained_when_copied` proves the adapter folder is self-contained: copy it to a temp location, run `scripts/rank_candidates.py --help` from the copy, and assert exit 0.

Replicate the test from a PowerShell prompt:

```powershell
$tmp = New-Item -ItemType Directory -Path (Join-Path $env:TEMP "openclaw-port-test") -Force
Copy-Item -Recurse harnesses/adapters/openclaw $tmp
Get-ChildItem $tmp/openclaw
Write-Output "---"
& python "$tmp/openclaw/scripts/rank_candidates.py" --help
Write-Output "EXIT $LASTEXITCODE"
Remove-Item -Recurse $tmp
```

Expected output (excerpt):

```
    Directory: C:\Users\...\AppData\Local\Temp\openclaw-port-test
Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----         8/02/2026   1:00 PM                openclaw

    Directory: ...\openclaw-port-test\openclaw
...
---
usage: rank_candidates.py [-h] [--input INPUT]

options:
  -h, --help     show this help message and exit
  --input INPUT

EXIT 0
```

If `EXIT $LASTEXITCODE` is non-zero, the copied folder is missing a file. Re-check Section 2's layout.

---

### 9. Full Pytest Run

The whole OpenClaw contract is asserted by `tests/test_openclaw_adapter.py`. Run it verbosely:

```powershell
rtk pytest tests/test_openclaw_adapter.py -v
```

Sample output (use `rtk proxy pytest` for the verbose line-by-line listing shown below):

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0 -- ...python.exe
...
collected 7 items

tests/test_openclaw_adapter.py::OpenClawAdapterLayoutTests::test_references_and_script_byte_identical_to_core PASSED [ 14%]
tests/test_openclaw_adapter.py::OpenClawAdapterLayoutTests::test_required_files_exist PASSED [ 28%]
tests/test_openclaw_adapter.py::OpenClawAdapterSkillMdTests::test_skill_md_body_matches_core_except_install_section PASSED [ 42%]
tests/test_openclaw_adapter.py::OpenClawAdapterSkillMdTests::test_skill_md_differs_from_codex_adapter_only_in_harness_and_install_section PASSED [ 57%]
tests/test_openclaw_adapter.py::OpenClawAdapterManifestTests::test_manifest_yaml_parses_with_expected_fields PASSED [ 71%]
tests/test_openclaw_adapter.py::OpenClawAdapterNoInstallerTests::test_no_installer_references_in_adapter PASSED [ 85%]
tests/test_openclaw_adapter.py::OpenClawAdapterPortabilityTests::test_adapter_is_self_contained_when_copied PASSED [100%]

============================== 7 passed in 0.39s ==============================
```

If you want the un-compacted line-by-line PASSED output, use `rtk proxy pytest tests/test_openclaw_adapter.py -v` (rtk's default filter compresses the per-test lines).

What each test class asserts:

| Test class | What it covers | Failure meaning |
|---|---|---|
| `OpenClawAdapterLayoutTests` | `SKILL.md`, `README.md`, `manifest.yaml`, four references, and `scripts/rank_candidates.py` all exist; the four reference files and the script are byte-identical to `harnesses/core/`. | A file is missing, or behavior content drifted from core. Re-copy from `harnesses/core/`. |
| `OpenClawAdapterSkillMdTests` | Adapter `SKILL.md` starts with `---\n`, has `harness: openclaw`, body (after frontmatter) starts with core body byte-for-byte, and appends `## OpenClaw Installation`. Also asserts the adapter differs from the Codex adapter only in the `harness:` line and the install-section name. | Frontmatter or install section drifted; or the Codex install section leaked in. |
| `OpenClawAdapterManifestTests` | `manifest.yaml` parses as YAML, `name == "openconcierge"`, `harness == "openclaw"`, `surfaces` equals `["openclaw-workspace", "openclaw-global"]`, `install` has all four keys. | Manifest edited by hand and lost a key, or it stopped being valid YAML. |
| `OpenClawAdapterNoInstallerTests` | No occurrence of `install.sh`, `install.ps1`, or `bootstrap/` anywhere under the adapter. | A banned installer string was introduced. |
| `OpenClawAdapterPortabilityTests` | Copying the adapter to a temp directory and running `python scripts/rank_candidates.py --help` exits 0. | The folder is not self-contained — a file is missing or the script is not byte-identical to core. |

You should also run the cross-harness tests so you know the OpenClaw additions did not break the rest of the repo:

```powershell
rtk pytest tests/test_openclaw_adapter.py tests/test_skill_contract.py tests/test_no_secrets.py -v
```

Expected: 12 passed (7 OpenClaw + 3 skill-contract + 2 no-secrets). And the full suite:

```powershell
rtk pytest tests/ -v
```

Expected: 66 passed, no skips.

---

### 10. Manual End-to-End Install + Conversational Test

This section requires OpenClaw installed and the OpenClaw binary on `PATH`. See `https://docs.openclaw.ai/cli/skills` for the install command. The `<owner>` placeholder in the manifest and README is **not** resolved until release — for everyday testing, use the **drop-in** install (it does not depend on a registry slug).

#### 10.1 Workspace install

From inside an OpenClaw workspace:

```powershell
openclaw skills install @<owner>/openconcierge
```

With the placeholder slug, expect a registry error like `unknown skill '@<owner>/openconcierge'`. That is expected — the official command is the spec target, but you cannot execute it until the release. The right test for "workspace install would work" is the drop-in flow below.

#### 10.2 Drop-in install (recommended for hands-on testing)

Copy the adapter folder to `~/.openclaw/skills/openconcierge/`, then restart OpenClaw:

```powershell
$dest = Join-Path $HOME ".openclaw/skills/openconcierge"
New-Item -ItemType Directory -Path $dest -Force | Out-Null
Copy-Item -Recurse harnesses/adapters/openclaw/* $dest
Get-ChildItem $dest
```

Expected output (the eight files from Section 2, now under `~/.openclaw/skills/openconcierge/`):

```
    Directory: C:\Users\<you>\.openclaw\skills\openconcierge
...
Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----         8/02/2026   1:00 PM                references
d-----         8/02/2026   1:00 PM                scripts
-a----         8/02/2026   1:00 PM           1500 README.md
-a----         8/02/2026   1:00 PM           4000 SKILL.md
-a----         8/02/2026   1:00 PM            500 manifest.yaml
```

Restart OpenClaw and confirm the skill is discovered. The exact command depends on OpenClaw's release; a typical sequence is:

```powershell
openclaw skills list
```

Expected output (the entry must be present, with `harness: openclaw` shown somewhere on the row):

```
name             version  scope     harness
openconcierge    0.1.0    global    openclaw
```

If `openconcierge` is absent, check the path (`$dest` above), confirm the `SKILL.md` starts with `---\n` (Section 4), and restart OpenClaw once more.

#### 10.3 Global install

The `--global` flag is the same surface as the drop-in install — it lands in `~/.openclaw/skills/openconcierge/`. The official command mirrors the workspace install:

```powershell
openclaw skills install @<owner>/openconcierge --global
```

Again, with the placeholder slug, expect a registry error. For the manifest contract, what matters is that `install.openclaw-global` is wired up and the user-facing path matches the drop-in. Re-run `openclaw skills list` and confirm `scope` shows `global` after the command succeeds under a real slug.

#### 10.4 Pillow-laptop scenario (in-scope)

Start an OpenClaw chat session and send:

```
/openconcierge Help me find a cooling pillow for side-sleepers. I'm a hot sleeper, want something under $100, must be latex-free, and I do freelance work on a laptop in bed so I need something that doesn't trap heat against my arm.
```

Assert the assistant's response includes:

1. **Interview.** No more than a handful of clarifying questions whose answers change the outcome (e.g., pillow fill, return policy). No generic intake items. The agent must end the interview as soon as the brief is sufficient to search.
2. **Ranked output.** A list of 2–4 qualified candidates. Each entry must include observed price, seller, why-it-fits anchored to the criteria, trade-offs, and direct source URLs.
3. **Sources.** At least one `https://` URL per candidate, calling out a product page or manufacturer page. URLs must be inspectable, not paraphrased.
4. **Trade-offs.** Honest, specific limitations (e.g., "needs refluffing", "not machine-washable"), not marketing language.
5. **Volatility reminder.** A short closing note that prices and stock should be re-verified before purchase.

For the `OBSERVED_LAPTOP` constraint, the agent should either fold it into a related sub-criterion (e.g., airflow through the cover) or label it as deferred — it must not be silently dropped.

#### 10.5 Out-of-scope scenario

Send a request that is NOT a shopping comparison:

```
/openconcierge Write me a Python script to parse CSV files.
```

Assert the response is a **brief decline** that points the user to the active host agent or to a more appropriate skill. The response must NOT manufacture product recommendations, must NOT do unrelated work, and must NOT silently expand the SKILL.md's scope.

#### 10.6 `OPENCLAW_STATE_DIR` override

The drop-in install path honors `OPENCLAW_STATE_DIR` when set. Repeat the drop-in install under a custom state directory:

```powershell
$custom = Join-Path $env:TEMP "openclaw-state"
New-Item -ItemType Directory -Path "$custom/skills/openconcierge" -Force | Out-Null
Copy-Item -Recurse harnesses/adapters/openclaw/* "$custom/skills/openconcierge"
$env:OPENCLAW_STATE_DIR = $custom
openclaw skills list
```

Expected output: `openconcierge` is listed (with `scope: global` or `scope: workspace` per OpenClaw's interpretation). Clean up afterward:

```powershell
Remove-Item -Recurse $custom
Remove-Item Env:OPENCLAW_STATE_DIR
```

If the override is not honored, the agent is consulting the wrong state directory — confirm `OPENCLAW_STATE_DIR` is exported into the same shell that launched OpenClaw.

#### 10.7 Forget preference flow

Begin a session and confirm a stable preference:

```
User: I prefer cooling pillows over memory foam. Please remember that.
Assistant: I'll remember "prefers cooling pillows over memory foam" as a confirmed preference. Confirm?
User: Yes.
/openconcierge show preferences
```

Expected output: the preference is listed.

Then exercise the forget flow:

```
User: /openconcierge forget preference "prefers cooling pillows over memory foam"
```

And confirm:

```
User: /openconcierge show preferences
```

Expected output: the preference is gone. The behavior must NOT promote transient facts (e.g., the brief in 10.4) to long-term preferences without explicit confirmation — `references/memory-and-privacy.md` lays out the rule.

---

### 11. Smoke Checklist

Tick each row before declaring the adapter done.

| # | Check | Section | Pass |
|---|-------|---------|------|
| 1 | Python 3.10+ available; `yaml` import works | 1 | `[ ]` |
| 2 | All eight files present under `harnesses/adapters/openclaw/` | 2 | `[ ]` |
| 3 | `manifest.yaml` parses with `harness: openclaw`, two surfaces, four install keys | 3 | `[ ]` |
| 4 | `SKILL.md` frontmatter starts with `---\n`, contains `harness: openclaw`, body starts with core body, appends `## OpenClaw Installation` | 4 | `[ ]` |
| 5 | Four reference files byte-identical to `harnesses/core/references/` | 5 | `[ ]` |
| 6 | `scripts/rank_candidates.py` byte-identical to core | 5 | `[ ]` |
| 7 | No `install.sh`, `install.ps1`, or `bootstrap/` strings anywhere in the adapter | 6 | `[ ]` |
| 8 | `rank_candidates.py --help` exits 0 | 7 | `[ ]` |
| 9 | All three ranking fixtures (`basic`, `ties`, `unknown-evidence`) exit 0 | 7 | `[ ]` |
| 10 | Copied adapter folder runs `rank_candidates.py --help` from a temp directory | 8 | `[ ]` |
| 11 | `rtk pytest tests/test_openclaw_adapter.py -v` reports 7 passed | 9 | `[ ]` |
| 12 | `rtk pytest tests/ -v` reports 66 passed (no regressions) | 9 | `[ ]` |
| 13 | Drop-in install lands the skill where OpenClaw discovers it | 10.2 | `[ ]` |
| 14 | Pillow-laptop scenario: interview + ranked output + sources + trade-offs present | 10.4 | `[ ]` |
| 15 | Out-of-scope scenario: brief decline, no manufactured output | 10.5 | `[ ]` |
| 16 | `OPENCLAW_STATE_DIR` override path is honored | 10.6 | `[ ]` |
| 17 | `forget preference` removes only the named preference | 10.7 | `[ ]` |

---

### 12. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `openclaw skills install @<owner>/openconcierge` errors with `unknown skill` | `<owner>/openconcierge` is a release-time placeholder; not registered on ClawHub yet. | Use the **drop-in install** (Section 10.2) for hands-on testing. The manifest contract is still satisfied. |
| Skill not discovered after drop-in | Wrong path, or OpenClaw was not restarted. | Copy to `~/.openclaw/skills/openconcierge/` (or `$OPENCLAW_STATE_DIR/skills/openconcierge/` when overridden). Restart OpenClaw. Re-run `openclaw skills list`. |
| `OpenClawAdapterLayoutTests::test_references_and_script_byte_identical_to_core` fails | A reference file or `rank_candidates.py` was edited in the adapter instead of `harnesses/core/`. | Edit `harnesses/core/` first, then re-copy the changed file(s) into `harnesses/adapters/openclaw/`, `harnesses/adapters/codex/`, and `harnesses/adapters/claude/` in the same commit per the rules in `harnesses/core/persona.md`. |
| `OpenClawAdapterSkillMdTests::test_skill_md_body_matches_core_except_install_section` fails | A drift between the core body and the adapter body, or the install section is missing. | Re-run the SKILL.md construction logic from `docs/superpowers/plans/2026-08-02-openconcierge-openclaw-adapter-plan.md` Task 6 — it reads `harnesses/core/SKILL.md` live. |
| `OpenClawAdapterSkillMdTests::test_skill_md_differs_from_codex_adapter_only_in_harness_and_install_section` fails | The Codex install section leaked into the OpenClaw adapter, or vice versa. | Each adapter must contain only its own install section (`## OpenClaw Installation` or `## Codex Installation`). Edit the adapter SKILL.md directly. |
| `OpenClawAdapterManifestTests` fails | Manifest is no longer valid YAML, or a required key is missing. | Confirm `harness: openclaw`, `surfaces: [openclaw-workspace, openclaw-global]`, and all four `install.*` keys. Re-run `python -c "import yaml; yaml.safe_load(open('harnesses/adapters/openclaw/manifest.yaml'))"` to catch syntax errors. |
| `OpenClawAdapterNoInstallerTests` fails | A banned string (`install.sh`, `install.ps1`, `bootstrap/`) is present in some file. | Per the spec, OpenClaw has no installer. Search the adapter and remove the offending reference. |
| `OpenClawAdapterPortabilityTests` fails | The copied folder is missing a file. | Re-check Section 2's file list. If `rank_candidates.py --help` fails, the script is either missing or not byte-identical to core. |
| `rank_candidates.py` exits 2 on a fixture | The fixture no longer matches the helper's contract (e.g., missing `product_url`, unknown `importance` value). | The helper rejects quietly. Re-check the fixture JSON against `tests/fixtures/ranking/basic.json` and the helper's documentation. |
| `OPENCLAW_STATE_DIR` override is ignored | `OPENCLAW_STATE_DIR` was exported in a different shell from the one that launched OpenClaw. | `export` (or `$env:OPENCLAW_STATE_DIR = ...`) in the same shell session, then restart OpenClaw from that session. |
| Pillow-laptop scenario omits sources or trade-offs | The host agent skipped the `## Recommendation Format` contract. | Verify the installed `SKILL.md` is the one from `harnesses/adapters/openclaw/` (Section 4) and that the install path is not an older copy. Restart OpenClaw after re-copy. |
| Out-of-scope scenario returns a manufactured recommendation | The host agent is not routing through the OpenConcierge skill, or a stale skill is loaded. | Confirm the skill is loaded with the correct version (`openclaw skills list`) and that `SKILL.md` starts with `## When to Use`. Re-copy from the adapter folder. |
| `forget preference` deletes more than the named preference | A stale skill is in effect, or the host agent is conflating user profiles. | Confirm the installed `references/memory-and-privacy.md` is byte-identical to core (Section 5). The `forget preference` action must remove only the named entry. |
