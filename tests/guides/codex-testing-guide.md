## Codex Adapter — End-to-End Testing Guide

This guide walks a human through every static, dynamic, and manual smoke check for the OpenConcierge **Codex adapter** at `harnesses/adapters/codex/`. Every step traces to a real artifact in the repository (a file, a fixture, or a test class in `tests/test_codex_adapter.py`). Run commands from the **repository root** unless told otherwise. All commands use **PowerShell 7+** syntax.

The seven tests in `tests/test_codex_adapter.py` are organized into five classes:

| Class | What it asserts |
|---|---|
| `CodexAdapterLayoutTests` | All required files exist; `references/` and `scripts/rank_candidates.py` are byte-identical to `harnesses/core/` |
| `CodexAdapterSkillMdTests` | SKILL.md frontmatter has `harness: codex`; body begins with the core body byte-for-byte; appends `## Codex Installation`; body *before* the install section is byte-identical to the Claude adapter's body *before* its install section |
| `CodexAdapterManifestTests` | Manifest parses via the custom parser with the expected field shape |
| `CodexAdapterNoInstallerTests` | No file under the adapter contains `install.sh`, `install.ps1`, or `bootstrap/` |
| `CodexAdapterPortabilityTests` | Copying the adapter folder to a temp dir and re-running `rank_candidates.py --help` exits 0 |

---

### 1. Prerequisites

- **Python 3.10+** (the project uses 3.12; both work because `rank_candidates.py` is stdlib-only).
- **Working directory**: the repository root (so relative paths like `harnesses/adapters/codex/...` resolve).
- **pytest** (already in the test environment) — used in step 10.
- **Codex CLI installed** — only required for the manual E2E checks in step 11. Skip steps 2–10 if you only want runtime E2E.

Distinguish the two modes:

| Mode | Steps | Needs Codex CLI? |
|---|---|---|
| Offline static checks | 2–10 | No |
| Runtime end-to-end | 11 | Yes |

Quick sanity check that the Python on `PATH` is recent enough:

```powershell
python --version
```

Expected output:

```
Python 3.10.x
```
(or newer; 3.12.x is what the project ships.)

---

### 2. Static layout check

The Codex adapter folder must contain exactly these eight paths (matches a droppable Codex skill):

```
harnesses/adapters/codex/SKILL.md
harnesses/adapters/codex/README.md
harnesses/adapters/codex/manifest.yaml
harnesses/adapters/codex/references/interviewing.md
harnesses/adapters/codex/references/memory-and-privacy.md
harnesses/adapters/codex/references/recommendations.md
harnesses/adapters/codex/references/research-and-evidence.md
harnesses/adapters/codex/scripts/rank_candidates.py
```

One-liner that fails fast if anything is missing:

```powershell
$expected = @(
    "harnesses/adapters/codex/SKILL.md",
    "harnesses/adapters/codex/README.md",
    "harnesses/adapters/codex/manifest.yaml",
    "harnesses/adapters/codex/references/interviewing.md",
    "harnesses/adapters/codex/references/memory-and-privacy.md",
    "harnesses/adapters/codex/references/recommendations.md",
    "harnesses/adapters/codex/references/research-and-evidence.md",
    "harnesses/adapters/codex/scripts/rank_candidates.py"
)
$missing = $expected | Where-Object { -not (Test-Path -LiteralPath $_) }
if ($missing) { Write-Error "missing: $($missing -join ', ')"; exit 1 } else { Write-Host "layout OK" }
```

Expected output:

```
layout OK
```

If any path is reported as missing, the adapter is incomplete — stop and re-create the missing files before continuing.

---

### 3. Manifest contract (custom parser aware)

The Codex `manifest.yaml` is **minimal and not a full YAML document** by design. It is parsed by the hand-rolled helper `_parse_codex_manifest_yaml` at the bottom of `tests/test_codex_adapter.py`. That helper supports:

- top-level `key: value` (with optional matching quotes),
- top-level `key:` followed by indented list items `- value`,
- top-level `key:` followed by indented `subkey: value` pairs (one level of nesting only).

**Do NOT use `yaml.safe_load` for this manifest in tests.** The test suite uses the hand-rolled parser on purpose.

Required shape (from `tests/test_codex_adapter.py::CodexAdapterManifestTests::test_manifest_yaml_parses_with_expected_fields`):

| Key | Required value | Asserted how |
|---|---|---|
| `name` | `openconcierge` (exact) | `assertEqual` |
| `harness` | `codex` (exact) | `assertEqual` |
| `version` | present | `assertIn` |
| `description` | present | `assertIn` |
| `license` | present | `assertIn` |
| `surfaces` | `["codex-cli"]` (exact) | `assertEqual` |
| `install.codex-cli` | present string | `assertIn` |
| `install.registry` | present string | `assertIn` |

Inspect the current manifest:

```powershell
Get-Content -LiteralPath "harnesses/adapters/codex/manifest.yaml"
```

Expected output:

```yaml
name: openconcierge
description: Research and compare products through a focused, source-backed shopping conversation.
version: 0.1.0
license: MIT
harness: codex
surfaces:
  - codex-cli
install:
  codex-cli: "drop the skill folder into ~/.codex/skills/openconcierge/ (or $CODEX_HOME/skills/openconcierge/)"
  registry: "npx skills add <owner>/<repo>  # <owner>/<repo> filled at release time"
```

Reproduce the custom parser in PowerShell and walk the file yourself:

```powershell
$text = Get-Content -LiteralPath "harnesses/adapters/codex/manifest.yaml" -Raw
$ast = python -c "
import sys
sys.path.insert(0, 'tests')
from test_codex_adapter import _parse_codex_manifest_yaml
import json
print(json.dumps(_parse_codex_manifest_yaml(sys.stdin.read()), indent=2))
" @($text)
$ast | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

Expected output (shape, values match the table above):

```json
{
  "name": "openconcierge",
  "description": "Research and compare products through a focused, source-backed shopping conversation.",
  "version": "0.1.0",
  "license": "MIT",
  "harness": "codex",
  "surfaces": ["codex-cli"],
  "install": {
    "codex-cli": "drop the skill folder into ~/.codex/skills/openconcierge/ (or $CODEX_HOME/skills/openconcierge/)",
    "registry": "npx skills add <owner>/<repo>  # <owner>/<repo> filled at release time"
  }
}
```

Notes:

- `surfaces` is parsed as a **list of strings** (no nested objects per item).
- `install` is parsed as a **one-level nested mapping** — anything deeper will break the parser.
- The `<owner>/<repo>` placeholder in `install.registry` is intentional and is filled at release time. Don't replace it here.

---

### 4. SKILL.md contract

The Codex `SKILL.md` must:

1. Start with YAML frontmatter (`---\n…\n---\n`).
2. Have `harness: codex` on its own line in the frontmatter.
3. Have a body (after the frontmatter) that **starts with the core `SKILL.md` body byte-for-byte**.
4. Append a `## Codex Installation` section after the core body.
5. **NOT** contain `## Claude Installation` or `## OpenClaw Installation`.

Inspect the frontmatter:

```powershell
$lines = Get-Content -LiteralPath "harnesses/adapters/codex/SKILL.md"
$lines | Select-Object -First 7
```

Expected output:

```
---
name: openconcierge
description: Research and compare products through a focused, source-backed shopping conversation.
version: 0.1.0
license: MIT
harness: codex
---
```

Confirm the `harness: codex` line is on its own:

```powershell
Select-String -Path "harnesses/adapters/codex/SKILL.md" -Pattern '^harness:\s*codex\s*$'
```

Expected output:

```
harnesses\adapters\codex\SKILL.md:6:harness: codex
```

Confirm the appended install section exists and the forbidden siblings are absent:

```powershell
$skill = Get-Content -LiteralPath "harnesses/adapters/codex/SKILL.md" -Raw
"## Codex Installation present:        $([bool]($skill -match '(?m)^## Codex Installation\s*$'))"
"## Claude Installation absent:        $(-not ($skill -match '(?m)^## Claude Installation\s*$'))"
"## OpenClaw Installation absent:      $(-not ($skill -match '(?m)^## OpenClaw Installation\s*$'))"
```

Expected output:

```
## Codex Installation present:        True
## Claude Installation absent:        True
## OpenClaw Installation absent:      True
```

Confirm the adapter body starts with the core body byte-for-byte (mirrors `test_skill_md_body_matches_core_except_install_section`):

```powershell
python -c "
from pathlib import Path
core = Path('harnesses/core/SKILL.md').read_text(encoding='utf-8')
adapter = Path('harnesses/adapters/codex/SKILL.md').read_text(encoding='utf-8')
end = core.find(chr(10) + '---' + chr(10), 4)
core_body = core[end + 5:]
adapter_start = adapter.find(chr(10) + '---' + chr(10), 4) + 5
adapter_body = adapter[adapter_start:]
print('adapter body starts with core body:', adapter_body.startswith(core_body))
print('appended tail length:', len(adapter_body) - len(core_body))
print('appended tail starts with ## Codex Installation:', adapter_body[len(core_body):].lstrip().startswith('## Codex Installation'))
"
```

Expected output:

```
adapter body starts with core body: True
appended tail length: 280
appended tail starts with ## Codex Installation: True
```

---

### 5. Reference byte-identity vs core

Every file under `harnesses/adapters/codex/references/` and `harnesses/adapters/codex/scripts/rank_candidates.py` must be **byte-identical** to the same path under `harnesses/core/`. The test enforces this in `CodexAdapterLayoutTests::test_references_and_script_byte_identical_to_core`.

`Compare-Object` walks five pairs and reports only files that differ:

```powershell
$pairs = @(
    @{ Core = "harnesses/core/references/interviewing.md";           Adapter = "harnesses/adapters/codex/references/interviewing.md" },
    @{ Core = "harnesses/core/references/memory-and-privacy.md";      Adapter = "harnesses/adapters/codex/references/memory-and-privacy.md" },
    @{ Core = "harnesses/core/references/recommendations.md";         Adapter = "harnesses/adapters/codex/references/recommendations.md" },
    @{ Core = "harnesses/core/references/research-and-evidence.md";   Adapter = "harnesses/adapters/codex/references/research-and-evidence.md" },
    @{ Core = "harnesses/core/scripts/rank_candidates.py";            Adapter = "harnesses/adapters/codex/scripts/rank_candidates.py" }
)

$drift = foreach ($p in $pairs) {
    $coreBytes    = Get-FileHash -LiteralPath $p.Core    -Algorithm SHA256
    $adapterBytes = Get-FileHash -LiteralPath $p.Adapter -Algorithm SHA256
    if ($coreBytes.Hash -ne $adapterBytes.Hash) {
        [PSCustomObject]@{ Core = $p.Core; Adapter = $p.Adapter; CoreHash = $coreBytes.Hash; AdapterHash = $adapterBytes.Hash }
    }
}
if ($drift) { $drift | Format-Table -AutoSize; Write-Error "drift detected"; exit 1 } else { Write-Host "all five pairs byte-identical" }
```

Expected output:

```
all five pairs byte-identical
```

Equivalent quick check via `fc.exe` (Windows-native, byte-level):

```powershell
fc.exe /b harnesses\core\scripts\rank_candidates.py harnesses\adapters\codex\scripts\rank_candidates.py
foreach ($f in @("interviewing.md","memory-and-privacy.md","recommendations.md","research-and-evidence.md")) {
    fc.exe /b "harnesses\core\references\$f" "harnesses\adapters\codex\references\$f"
}
```

Expected output (each line ends with `FC: no differences encountered`):

```
Comparing files HARNESSES\CORE\SCRIPTS\rank_candidates.py and HARNESSES\ADAPTERS\CODEX\SCRIPTS\RANK_CANDIDATES.PY
FC: no differences encountered
...
```

If any pair drifts, copy the file from core into the adapter (`Copy-Item -Force`) and re-run.

---

### 6. Cross-adapter consistency check

The body of `harnesses/adapters/codex/SKILL.md` **before** `## Codex Installation` must be byte-identical to the body of `harnesses/adapters/claude/SKILL.md` **before** `## Claude Installation`. Enforced by `CodexAdapterSkillMdTests::test_skill_md_differs_from_claude_adapter_only_in_harness_and_install_section`.

```powershell
python -c "
from pathlib import Path

def strip_frontmatter(text):
    end = text.find(chr(10) + '---' + chr(10), 4)
    return text[end + 5:]

codex = strip_frontmatter(Path('harnesses/adapters/codex/SKILL.md').read_text(encoding='utf-8'))
claude = strip_frontmatter(Path('harnesses/adapters/claude/SKILL.md').read_text(encoding='utf-8'))

codex_pre = codex[:codex.index('## Codex Installation')]
claude_pre = claude[:claude.index('## Claude Installation')]

print('pre-install body byte-identical between codex and claude adapters:', codex_pre == claude_pre)
print('pre-install body length:', len(codex_pre))
"
```

Expected output:

```
pre-install body byte-identical between codex and claude adapters: True
pre-install body length: 5679
```

Visually scan the diff between the two SKILL.md files. You should see exactly two changes: the `harness:` line and the install section title:

```powershell
fc.exe /b harnesses\adapters\codex\SKILL.md harnesses\adapters\claude\SKILL.md | Select-String -Pattern '^Comparing' -NotMatch
```

Expected (abridged):

```
***** harnesses\adapters\codex\SKILL.md
... harness: codex ...
***** harnesses\adapters\claude\SKILL.md
... harness: claude ...
... ## Claude Installation ...
... ## Codex Installation ...
```

---

### 7. No-installer-needle rule

The adapter MUST NOT contain `install.sh`, `install.ps1`, or `bootstrap/`. Forbidden needles are defined at `tests/test_codex_adapter.py::CodexAdapterNoInstallerTests::FORBIDDEN_NEEDLES`.

Reproduce the needle walk with PowerShell:

```powershell
$needles = @("install.sh","install.ps1","bootstrap/")
$hits = foreach ($file in Get-ChildItem -LiteralPath "harnesses/adapters/codex" -Recurse -File) {
    if ($file.Extension -eq ".pyc") { continue }
    $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
    foreach ($needle in $needles) {
        if ($content -and $content.Contains($needle)) {
            [PSCustomObject]@{ File = $file.FullName.Substring($PWD.Path.Length + 1); Needle = $needle }
        }
    }
}
if ($hits) { $hits | Format-Table -AutoSize; Write-Error "forbidden needles found"; exit 1 } else { Write-Host "no installer needles" }
```

Expected output:

```
no installer needles
```

If anything hits, edit the offending file to remove the literal string. The most common offender is a comment that mentions the Hermes installer path.

---

### 8. Deterministic ranking helper

`scripts/rank_candidates.py` is stdlib-only (no third-party deps) and is the same helper called by every harness. It supports `--help` and `--input <path>` (or stdin via `--input -`).

Run `--help` first:

```powershell
python harnesses/adapters/codex/scripts/rank_candidates.py --help
```

Expected output (exit 0):

```
usage: rank_candidates.py [-h] [--input INPUT]

options:
  -h, --help     show this help message and exit
  --input INPUT
```

Then run each fixture in `tests/fixtures/ranking/`:

```powershell
python harnesses/adapters/codex/scripts/rank_candidates.py --input tests/fixtures/ranking/basic.json
python harnesses/adapters/codex/scripts/rank_candidates.py --input tests/fixtures/ranking/ties.json
python harnesses/adapters/codex/scripts/rank_candidates.py --input tests/fixtures/ranking/unknown-evidence.json
```

Expected: all three exit 0 and print JSON with `{"ranked":[…],"unranked":[…],"rejected":[…]}`. The `basic.json` run rejects `Over Budget Pillow` (`over_budget`) and `Unavailable Pillow` (`region_unavailable`) and ranks `Valid Cooling Pillow` with `fit_score: 0.8`.

A single one-liner that asserts exit 0 for all three fixtures:

```powershell
$fixtures = @("basic","ties","unknown-evidence")
foreach ($f in $fixtures) {
    $p = Start-Process -FilePath python -ArgumentList @(
        "harnesses/adapters/codex/scripts/rank_candidates.py",
        "--input",
        "tests/fixtures/ranking/$f.json"
    ) -NoNewWindow -PassThru -Wait -RedirectStandardOutput "tests/fixtures/ranking/$f.out"
    if ($p.ExitCode -ne 0) { Write-Error "$f.json failed with exit $($p.ExitCode)"; exit 1 }
    Write-Host "$f.json OK"
}
```

Expected output:

```
basic.json OK
ties.json OK
unknown-evidence.json OK
```

---

### 9. Portability check

Mirrors `CodexAdapterPortabilityTests::test_adapter_is_self_contained_when_copied`: copy the adapter folder to a temp dir and re-run `rank_candidates.py --help` from the copy. The folder must be self-contained (no symlinks back to the repo).

```powershell
$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("codex-port-" + [Guid]::NewGuid().ToString("N").Substring(0,8))
$dest = Join-Path $tmp "openconcierge"
Copy-Item -LiteralPath "harnesses/adapters/codex" -Destination $dest -Recurse

# Confirm the eight expected files are present in the copy.
$expected = @(
    "SKILL.md","README.md","manifest.yaml",
    "references/interviewing.md","references/memory-and-privacy.md",
    "references/recommendations.md","references/research-and-evidence.md",
    "scripts/rank_candidates.py"
)
$missing = $expected | Where-Object { -not (Test-Path -LiteralPath (Join-Path $dest $_)) }
if ($missing) { Write-Error "copy missing: $($missing -join ', ')"; exit 1 }

# Run the ranking helper from the copy.
$proc = Start-Process -FilePath python -ArgumentList @(
    (Join-Path $dest "scripts/rank_candidates.py"), "--help"
) -NoNewWindow -PassThru -Wait -RedirectStandardOutput "$tmp\help.out"
if ($proc.ExitCode -ne 0) { Write-Error "rank_candidates.py --help exited $($proc.ExitCode)"; exit 1 }
Write-Host "portable copy at $dest, --help exit 0"
Remove-Item -LiteralPath $tmp -Recurse -Force
```

Expected output:

```
portable copy at C:\Users\...\AppData\Local\Temp\codex-port-XXXXXXXX\openconcierge, --help exit 0
```

---

### 10. Full pytest run

Run the Codex-specific suite, with verbose output so each test class is visible:

```powershell
python -m pytest tests/test_codex_adapter.py -v
```

Expected output (seven tests pass, five classes):

```
test_codex_adapter.py::CodexAdapterLayoutTests::test_required_files_exist ........................ PASSED
test_codex_adapter.py::CodexAdapterLayoutTests::test_references_and_script_byte_identical_to_core  PASSED
test_codex_adapter.py::CodexAdapterSkillMdTests::test_skill_md_body_matches_core_except_install_section PASSED
test_codex_adapter.py::CodexAdapterSkillMdTests::test_skill_md_differs_from_claude_adapter_only_in_harness_and_install_section PASSED
test_codex_adapter.py::CodexAdapterManifestTests::test_manifest_yaml_parses_with_expected_fields .... PASSED
test_codex_adapter.py::CodexAdapterNoInstallerTests::test_no_installer_references_in_adapter ......... PASSED
test_codex_adapter.py::CodexAdapterPortabilityTests::test_adapter_is_self_contained_when_copied ..... PASSED

============== 7 passed in X.XXs ==============
```

If you want only a specific class, filter by class name:

```powershell
python -m pytest tests/test_codex_adapter.py::CodexAdapterSkillMdTests -v
```

How to interpret failures:

| Failing test | Likely cause | Fix |
|---|---|---|
| `CodexAdapterLayoutTests::test_required_files_exist` | A file is missing or moved | Re-create per step 2's expected list |
| `CodexAdapterLayoutTests::test_references_and_script_byte_identical_to_core` | A copy in `references/` or `scripts/` drifted from `harnesses/core/` | `Copy-Item -Force` from core into the adapter |
| `CodexAdapterSkillMdTests::test_skill_md_body_matches_core_except_install_section` | Frontmatter wrong, body edited, or install section missing | Compare to `harnesses/core/SKILL.md`; ensure `harness: codex` line is in frontmatter and `## Codex Installation` is appended |
| `CodexAdapterSkillMdTests::test_skill_md_differs_from_claude_adapter_only_in_harness_and_install_section` | Body was edited between adapters, or the wrong install section name | Diff `harnesses/adapters/codex/SKILL.md` vs `harnesses/adapters/claude/SKILL.md` (step 6) |
| `CodexAdapterManifestTests::test_manifest_yaml_parses_with_expected_fields` | Field missing/wrong, list-vs-dict mismatch, or nested deeper than one level | Compare to step 3's manifest shape |
| `CodexAdapterNoInstallerTests::test_no_installer_references_in_adapter` | A file references `install.sh` / `install.ps1` / `bootstrap/` | Remove the literal; check README comments especially |
| `CodexAdapterPortabilityTests::test_adapter_is_self_contained_when_copied` | A required file didn't survive copytree, or the script can't run standalone | Re-run step 9 manually; if the file is missing, recreate it |

Then run the cross-harness tests so you know the Codex adapter hasn't disturbed other surfaces:

```powershell
python -m pytest tests/test_skill_contract.py tests/test_no_secrets.py -v
```

Expected: all `SkillContractTests` (3) and `RepositorySafetyTests` (2) pass.

---

### 11. Manual end-to-end install + conversational test

This section requires the Codex CLI to be installed and on `PATH`. Skip on machines that only run the offline suite.

#### 11a. Drop-in install

Locate the Codex skills root. Codex looks at `$HOME/.codex/skills/` by default, but honors `$CODEX_HOME` if it is set.

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$skillRoot = Join-Path $codexHome "skills"
$dest      = Join-Path $skillRoot "openconcierge"

Write-Host "codexHome: $codexHome"
Write-Host "skillRoot: $skillRoot"
Write-Host "dest:      $dest"
```

Copy the adapter folder (PowerShell-friendly, mirrors a release artifact):

```powershell
New-Item -ItemType Directory -Force -Path $skillRoot | Out-Null
if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
Copy-Item -LiteralPath "harnesses/adapters/codex" -Destination $dest -Recurse
```

Confirm the eight files are in place under `$dest`:

```powershell
Get-ChildItem -LiteralPath $dest -Recurse -File |
    Where-Object { $_.Extension -ne ".pyc" } |
    Select-Object -ExpandProperty FullName
```

Expected output (eight files; relative paths match step 2):

```
...\skills\openconcierge\SKILL.md
...\skills\openconcierge\README.md
...\skills\openconcierge\manifest.yaml
...\skills\openconcierge\references\interviewing.md
...\skills\openconcierge\references\memory-and-privacy.md
...\skills\openconcierge\references\recommendations.md
...\skills\openconcierge\references\research-and-evidence.md
...\skills\openconcierge\scripts\rank_candidates.py
```

Restart Codex, then invoke the skill by typing `/openconcierge` in the prompt.

#### 11b. Registry install (when published)

```powershell
npx skills add <owner>/<repo>
```

> `<owner>/<repo>` is a release-time placeholder; until the project publishes to a Codex-compatible skills registry, use the drop-in path above. The same adapter folder is what a registry indexer would fetch, so once `<owner>/<repo>` is filled in, this command installs the same content.

#### 11c. Conversational scenarios

Walk through each scenario in a fresh Codex session. Each scenario lists what the agent should do, per `references/*.md` and `SKILL.md`.

1. **Pillow scenario (in scope, full flow).**
   Type: `/openconcierge I'm a side sleeper in the US with a latex allergy, budget $100, and I want a cooling pillow.`
   Expect:
   - Interviewing only fires on questions whose answers change the outcome (latex allergy is `must`, cooling is `core`, side sleeper is `preference`); see `references/interviewing.md`.
   - Search capability resolves via Codex's built-in tools per `## Search Capability Resolution`.
   - Candidate evidence is normalized per `references/research-and-evidence.md`; `match: strong/partial` requires an `http(s)` URL.
   - The agent invokes `scripts/rank_candidates.py` and reports `fit_score` and `score_breakdown`.
   - Output follows `references/recommendations.md` (need, assumptions, 2–4 options, comparison, volatility reminder).
   - Over-budget or unshippable candidates are rejected with stable reasons (`over_budget`, `region_unavailable`, `unverified_must_have`, etc.).

2. **Out-of-scope scenario.**
   Type: `/openconcierge Help me debug a Python traceback.`
   Expect: brief decline; the agent refers you to the host agent or a different skill — no ranking, no product research, no fabricated prices.

3. **"Use your judgment" scenario.**
   Type: `/openconcierge I want a new backpack, just use your judgment for the rest.`
   Expect: the agent picks sensible defaults, **states each assumption in plain language**, and **labels every assumption in the final recommendation** (see `## Clarifying Questions` and `references/recommendations.md`). It should not ask further intake questions.

4. **`forget preference` scenario.**
   - First, run a normal session and let the agent remember a stable preference (e.g. "Remember: I prefer merino wool over synthetic for base layers."). Confirm the agent asks for explicit confirmation before persisting.
   - Then type: `/openconcierge forget preference: merino base layers`.
   - Expect: the named preference is removed. Run `/openconcierge show preferences` to verify.
   - Sensitive constraints (health, allergies, disability-related needs) are used for the current task but not stored as durable preferences unless the user explicitly asks. See `references/memory-and-privacy.md`.

#### 11d. CODEX_HOME override path

The SKILL.md install section mentions both `~/.codex/skills/openconcierge/` and `$CODEX_HOME/skills/openconcierge/`. Verify the override:

```powershell
$altHome = Join-Path ([System.IO.Path]::GetTempPath()) ("codex-home-" + [Guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Force -Path (Join-Path $altHome "skills") | Out-Null
$env:CODEX_HOME = $altHome
Copy-Item -LiteralPath "harnesses/adapters/codex" -Destination (Join-Path $altHome "skills\openconcierge") -Recurse

Test-Path -LiteralPath (Join-Path $env:CODEX_HOME "skills\openconcierge\SKILL.md")
```

Expected output:

```
True
```

Launch Codex with `$env:CODEX_HOME` still set and confirm `/openconcierge` is discovered from the temp `codex-home-XXXXXXXX` directory. Clean up afterwards:

```powershell
Remove-Env:CODEX_HOME -ErrorAction SilentlyContinue  # PowerShell 7+ (see note below)
Remove-Item -LiteralPath $altHome -Recurse -Force
```

> PowerShell 7 note: the canonical way to unset an env var is `$env:CODEX_HOME = $null`. The `Remove-Env:` syntax above is a placeholder — substitute `$env:CODEX_HOME = $null` if your shell version differs.

---

### 12. Smoke checklist

Single table covering all checks.

| # | Check | Command (essence) | Pass criterion |
|---|---|---|---|
| 1 | Layout has 8 files | `Test-Path` on each path | All present |
| 2 | Manifest parses with expected fields | Run `_parse_codex_manifest_yaml` from the test | `name=openconcierge`, `harness=codex`, `surfaces=["codex-cli"]`, `install.{codex-cli,registry}` present |
| 3 | SKILL.md frontmatter has `harness: codex` | `Select-String -Pattern '^harness:\s*codex\s*$'` | One match on its own line |
| 4 | SKILL.md body starts with core body byte-for-byte | `adapter_body.startswith(core_body)` after stripping frontmatter | `True` |
| 5 | SKILL.md appends `## Codex Installation` | substring search in tail | Present |
| 6 | SKILL.md does not contain `## Claude Installation` or `## OpenClaw Installation` | substring search | Both absent |
| 7 | `references/*` and `scripts/rank_candidates.py` byte-identical to core | `Compare-Object` / `fc.exe /b` | No diff |
| 8 | Codex body (before install) == Claude body (before install) | `codex_pre == claude_pre` | `True` |
| 9 | No `install.sh` / `install.ps1` / `bootstrap/` anywhere in adapter | needle walk | Zero hits |
| 10 | `rank_candidates.py --help` exits 0 | run script | Exit 0, prints usage |
| 11 | All three ranking fixtures exit 0 | `python … --input tests/fixtures/ranking/<name>.json` × 3 | Three exit 0 |
| 12 | Adapter is self-contained when copied to temp dir | `Copy-Item -Recurse` + run script from copy | Exit 0 |
| 13 | `pytest tests/test_codex_adapter.py -v` | full pytest | 7 passed |
| 14 | Cross-harness tests still pass | `pytest tests/test_skill_contract.py tests/test_no_secrets.py -v` | All pass |
| 15 | Manual drop-in install + `/openconcierge` works | copy to `~/.codex/skills/openconcierge/`, restart Codex | Skill discovered |
| 16 | `CODEX_HOME` override path | set `$env:CODEX_HOME`, copy, restart | Skill discovered from alt root |

---

### 13. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Skill not discovered after drop-in | Codex not restarted; wrong destination path; copied a parent directory instead of the adapter folder | Restart Codex; confirm `$dest\SKILL.md` and `$dest\manifest.yaml` exist directly under `openconcierge/` (not nested in another folder) |
| Skill not discovered under `$CODEX_HOME` | `$env:CODEX_HOME` was not set in the same shell that launched Codex | Export it in the same shell session, or set it system-wide before launching |
| `references/*.md` content looks stale | `harnesses/core/` was updated but the adapter wasn't synced | Re-copy per step 5; remember the sync rule in `harnesses/core/persona.md` |
| `scripts/rank_candidates.py --help` exits non-zero | The file isn't byte-identical to core, or Python is < 3.10 | Re-copy from core; check `python --version` |
| `npx skills add <owner>/<repo>` not yet wired | Release-time placeholder not filled in | Use the drop-in path; revisit after the first release |
| Custom manifest parser trips | Multi-level YAML added (e.g. nested lists under `install`) | Flatten to one level; the parser only supports top-level `key: value`, list-of-strings, and one-level nested mappings |
| `assertEqual(manifest["surfaces"], ["codex-cli"])` fails | Someone added a second surface, or used a different shape | `surfaces` must be a list of strings with exactly `["codex-cli"]` today; revisit when Codex adds a new surface |
| `assertNotIn("## Claude Installation", codex_text)` fails | Adapter SKILL.md got edited to mention Claude by name | Rename or remove the reference; only `## Codex Installation` should appear in the install section |
| `assertEqual(codex_pre, claude_pre)` fails | A behavioral change landed in `harnesses/core/SKILL.md` but the adapters weren't updated in lockstep | Diff all three SKILL.md files; bring them back in sync per the maintenance rule |
| Portability test fails on `rank_candidates.py --help` | Python missing or script not copied | `Test-Path` the script in the temp copy; ensure `Copy-Item -Recurse` was used |
| Forbidden needle (`install.sh`, `install.ps1`, `bootstrap/`) found in a comment | A doc or comment mentions the Hermes installer path | Remove the literal; the adapter must not reference any installer convention |
| Manifest `harness:` value drifts to something else | Manual edit | Restore `harness: codex` exactly (lowercase, single space after colon) |
