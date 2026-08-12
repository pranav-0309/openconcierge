# OpenConcierge — Multi-Harness End-to-End Testing Guide

A consolidated, follow-along testing guide for every harness shipped under `harnesses/` in the OpenConcierge repository. The four harnesses, in the order a maintainer should test them:

1. **Hermes** — the core harness at `harnesses/core/`. This is the canonical source that all adapters extend.
2. **OpenClaw** (referred to in this guide as "open code") — the OpenClaw CLI adapter at `harnesses/adapters/openclaw/`.
3. **Claude** (referred to in this guide as "claude") — the Claude adapter at `harnesses/adapters/claude/`, covering Claude Code, Claude Desktop, and claude.ai Chat.
4. **Codex** — the Codex CLI adapter at `harnesses/adapters/codex/`.

> **How to use this guide.** Each section is self-contained: read the Hermes section first, then run its commands top-to-bottom before moving to the next harness. Every PowerShell snippet is written for PowerShell 7+ on Windows and is run from the **repository root** (`C:\Users\ACER\Documents\opencode_projects\open-concierge`). All offline static checks run with no network and no live model call.
>
> **Before you start.** Confirm the toolchain:
>
> ```powershell
> $PSVersionTable.PSVersion       # expect Major >= 7
> python --version                 # expect 3.10+ (3.12 recommended)
> python -m pytest --version       # expect 7.x or 8.x
> git status                       # expect "nothing to commit, working tree clean"
> ```

## Contents

- [1. Hermes harness — End-to-End Testing Guide](#1-hermes-harness--end-to-end-testing-guide)
- [2. OpenClaw adapter ("open code") — End-to-End Testing Guide](#2-openclaw-adapter-open-code--end-to-end-testing-guide)
- [3. Claude adapter ("claude") — End-to-End Testing Guide](#3-claude-adapter-claude--end-to-end-testing-guide)
- [4. Codex adapter — End-to-End Testing Guide](#4-codex-adapter--end-to-end-testing-guide)

---

# 1. Hermes harness — End-to-End Testing Guide


This guide covers the **Hermes core harness** at `harnesses/core/`. This is the canonical source that the adapter harnesses (`harnesses/adapters/claude/`, `harnesses/adapters/codex/`, `harnesses/adapters/openclaw/`) extend. Everything below assumes PowerShell 7+ on Windows, the OpenConcierge repo as the working directory, and Python 3.10+ on `PATH`. All static checks (steps 2–9) run fully offline — no live network or live model call is required.

> **Scope reminder.** This document only verifies `harnesses/core/` (and the test suite that exercises it). The Hermes distribution itself lives at `skills/openconcierge/` and is owned by `tests/test_distribution_layout.py`. The two copies must stay in sync per `harnesses/core/persona.md`.

---

### 1. Prerequisites

**Tools needed:**

- PowerShell 7+ on `PATH` (run `$PSVersionTable.PSVersion` to confirm).
- Python 3.10+ on `PATH` (`python --version`). The reference interpreter used to develop this repo is 3.12.x. `scripts/rank_candidates.py` is standard-library only — no `pip install` needed.
- `pytest` on `PATH`. If you do not have it: `python -m pip install pytest`.
- The repo cloned and the working tree clean (`git status`).
- For the manual conversational walkthrough in step 11, an active Hermes Agent installation reachable by your user account (typically under `~/.hermes/`).

**Repo layout assumed:**

```
open-concierge/
├── distribution.yaml            # declares Hermes compatibility
├── SOUL.md                      # Hermes persona, sibling of harnesses/core/persona.md
├── harnesses/
│   └── core/                    # THIS GUIDE'S SCOPE
│       ├── SKILL.md
│       ├── manifest.yaml
│       ├── persona.md
│       ├── references/
│       │   ├── interviewing.md
│       │   ├── research-and-evidence.md
│       │   ├── recommendations.md
│       │   └── memory-and-privacy.md
│       └── scripts/
│           └── rank_candidates.py
├── skills/openconcierge/        # Hermes distribution (touched only by installer)
└── tests/
    ├── test_distribution_layout.py
    ├── test_no_secrets.py
    ├── test_rank_candidates.py
    ├── test_skill_contract.py
    └── fixtures/ranking/{basic,ties,unknown-evidence}.json
```

```powershell
$PSVersionTable.PSVersion              # expect Major >= 7
python --version                        # expect 3.10+ (3.12 recommended)
python -m pytest --version              # expect 7.x or 8.x
git status                              # expect "nothing to commit, working tree clean"
```

---

### 2. Static layout check

`harnesses/core/` must contain exactly these eight files (no more, no fewer, for a green check). Each has a role; the table at the end of this section maps role → file.

```powershell
$expected = @(
  'manifest.yaml',
  'SKILL.md',
  'persona.md',
  'references/interviewing.md',
  'references/research-and-evidence.md',
  'references/recommendations.md',
  'references/memory-and-privacy.md',
  'scripts/rank_candidates.py'
) | ForEach-Object { Join-Path 'harnesses/core' $_ }

$missing = $expected | Where-Object { -not (Test-Path -LiteralPath $_) }
if ($missing) { "MISSING:`n$($missing -join "`n")" } else { "OK: 8/8 core files present" }
```

Expected:

```text
OK: 8/8 core files present
```

**Manual list** (cross-check the directory tree):

```powershell
Get-ChildItem -LiteralPath harnesses/core -Recurse -File |
  Where-Object { $_.FullName -notmatch '__pycache__' } |
  Select-Object FullName
```

Expected (paths only):

```text
harnesses\core\SKILL.md
harnesses\core\manifest.yaml
harnesses\core\persona.md
harnesses\core\references\interviewing.md
harnesses\core\references\memory-and-privacy.md
harnesses\core\references\recommendations.md
harnesses\core\references\research-and-evidence.md
harnesses\core\scripts\rank_candidates.py
```

| Role | File |
|---|---|
| YAML manifest for distribution tools | `harnesses/core/manifest.yaml` |
| Skill body loaded by the host agent | `harnesses/core/SKILL.md` |
| Voice + hard rules (mirror of `SOUL.md`) | `harnesses/core/persona.md` |
| Clarifying-question expansion | `references/interviewing.md` |
| Search resolution + candidate schema | `references/research-and-evidence.md` |
| Output format contract | `references/recommendations.md` |
| Memory + privacy rules | `references/memory-and-privacy.md` |
| Deterministic ranking helper | `scripts/rank_candidates.py` |

> Anything extra under `harnesses/core/` is allowed but not consumed by the rest of the repo. Anything missing is a release blocker.

---

### 3. YAML manifest contract

`harnesses/core/manifest.yaml` declares the harness identity. Four keys are required; values are exact strings today.

```powershell
Get-Content -LiteralPath harnesses/core/manifest.yaml
```

Expected:

```text
name: openconcierge
description: Research and compare products through a focused, source-backed shopping conversation.
version: 0.1.0
license: MIT
```

Assert each field with Python (no extra dependency on `pyyaml`):

```powershell
python -c @'
from pathlib import Path
text = Path("harnesses/core/manifest.yaml").read_text(encoding="utf-8")
required = {
    "name": "openconcierge",
    "description": "Research and compare products through a focused, source-backed shopping conversation.",
    "version": "0.1.0",
    "license": "MIT",
}
missing = [k for k in required if f"{k}:" not in text]
wrong = [f"{k}={required[k]!r}" for k in required if f"{k}: {required[k]}" not in text]
print("MISSING_KEYS:" if missing else "", *missing, sep="\n")
print("WRONG_VALUES:" if wrong else "", *wrong, sep="\n")
print("OK: manifest.yaml contract holds" if not missing and not wrong else "FAIL")
'@
```

Expected:

```text
OK: manifest.yaml contract holds
```

If `MISSING_KEYS:` or `WRONG_VALUES:` prints anything, fix `manifest.yaml` before continuing.

---

### 4. SKILL.md contract

`SKILL.md` is two things in one file: a YAML frontmatter block (top four lines between `---` fences) and a markdown body with nine required `## ` headings.

**Required frontmatter keys:** `name`, `description`, `version`, `license`. Same values as `manifest.yaml`.

**Required body sections (in order):**

| # | Heading | Source it expands |
|---|---|---|
| 1 | `## When to Use` | top-level |
| 2 | `## Clarifying Questions` | `references/interviewing.md` |
| 3 | `## Search Capability Resolution` | `references/research-and-evidence.md` |
| 4 | `## Candidate Evidence` | `references/research-and-evidence.md` |
| 5 | `## Evidence and Ranking` | `scripts/rank_candidates.py` |
| 6 | `## Recommendation Format` | `references/recommendations.md` |
| 7 | `## Memory and Privacy` | `references/memory-and-privacy.md` |
| 8 | `## Failure Handling` | top-level |
| 9 | `## Verification` | top-level |

```powershell
$required = @(
  '## When to Use',
  '## Clarifying Questions',
  '## Search Capability Resolution',
  '## Candidate Evidence',
  '## Evidence and Ranking',
  '## Recommendation Format',
  '## Memory and Privacy',
  '## Failure Handling',
  '## Verification'
)

$text = Get-Content -LiteralPath harnesses/core/SKILL.md -Raw
$missing = $required | Where-Object { $_ -notin ($text -split "`n") }
if ($missing) { "MISSING:`n$($missing -join "`n")" } else { "OK: all 9 SKILL.md headings present" }
```

Expected:

```text
OK: all 9 SKILL.md headings present
```

**Frontmatter assertion** (must start with `---`, must declare all four keys, must NOT name a search provider in any `requires`/`depends on` line):

```powershell
python -c @'
from pathlib import Path
import re
text = Path("harnesses/core/SKILL.md").read_text(encoding="utf-8")
assert text.startswith("---\n"), "missing opening frontmatter fence"
fm_block, _, body = text.partition("---\n")
fm_block, _, body = body.partition("---\n")  # second fence
for key in ("name", "description", "version", "license"):
    assert re.search(rf"(?m)^{key}:\s*\S", fm_block), f"frontmatter missing {key}"
assert not re.search(r"(?im)^\s*requires_tools:", text), "requires_tools must not appear"
assert not re.search(r"(?i)(requires|depends on).*(exa|tavily|serpapi|serper|brave|duckduckgo)", text), "no provider dependency"
print("OK: SKILL.md frontmatter + provider-neutral contract holds")
'@
```

Expected:

```text
OK: SKILL.md frontmatter + provider-neutral contract holds
```

---

### 5. Reference-doc completeness

Each of the four `references/*.md` files must exist and must be **cross-referenced by SKILL.md** with a `references/<name>.md` mention. This catches the common mistake of editing one without updating the other.

```powershell
$refs = @('interviewing.md', 'research-and-evidence.md', 'recommendations.md', 'memory-and-privacy.md')
$skill = Get-Content -LiteralPath harnesses/core/SKILL.md -Raw

$missingFile = $refs | Where-Object { -not (Test-Path -LiteralPath "harnesses/core/references/$_") }
$unlinked = $refs | Where-Object { $skill -notlike "*references/$_*" }

if ($missingFile -or $unlinked) {
  "MISSING_FILES: $($missingFile -join ', ')"
  "UNLINKED_IN_SKILL: $($unlinked -join ', ')"
} else {
  "OK: 4/4 reference docs exist and are referenced from SKILL.md"
}
```

Expected:

```text
OK: 4/4 reference docs exist and are referenced from SKILL.md
```

**Cross-reference sanity** — each reference doc opens by saying which `SKILL.md` section it expands:

```powershell
$openers = @{
  'interviewing.md'             = '## Clarifying Questions'
  'research-and-evidence.md'    = '## Search Capability Resolution'
  'recommendations.md'          = '## Recommendation Format'
  'memory-and-privacy.md'       = '## Memory and Privacy'
}

foreach ($kv in $openers.GetEnumerator()) {
  $path = "harnesses/core/references/$($kv.Key)"
  $first20 = (Get-Content -LiteralPath $path -TotalCount 5) -join "`n"
  if ($first20 -notmatch [regex]::Escape($kv.Value)) {
    "WRONG OPENER: $path should reference $($kv.Value)"
  } else {
    "OK opener: $($kv.Key) -> $($kv.Value)"
  }
}
```

Expected:

```text
OK opener: interviewing.md -> ## Clarifying Questions
OK opener: research-and-evidence.md -> ## Search Capability Resolution
OK opener: recommendations.md -> ## Recommendation Format
OK opener: memory-and-privacy.md -> ## Memory and Privacy
```

---

### 6. Deterministic ranking helper

`scripts/rank_candidates.py` is the only executable in the core harness. It reads a JSON payload (task + candidates) on stdin (or via `--input`) and writes `{ranked, unranked, rejected}` to stdout. Standard-library only.

**Step 6.1 — `--help` works (exit code 0):**

```powershell
python harnesses/core/scripts/rank_candidates.py --help
```

Expected:

```text
usage: rank_candidates.py [-h] [--input INPUT]

options:
  -h, --help     show this help message and exit
  --input INPUT
```

**Step 6.2 — `basic.json` (one valid candidate, one over-budget, one region-unavailable):**

```powershell
Get-Content -LiteralPath tests/fixtures/ranking/basic.json -Raw |
  python harnesses/core/scripts/rank_candidates.py
```

Expected (abridged — exit code 0, valid JSON, exactly one ranked item):

```text
{
  "ranked": [
    {
      "criteria": [ /* cooling / side-sleeper support / latex-free */ ],
      "fit_score": 0.8,
      "name": "Valid Cooling Pillow",
      "score_breakdown": { "cooling": 3.0, "side-sleeper support": 1.0 },
      ...
    }
  ],
  "rejected": [
    { "name": "Over Budget Pillow",  "reason": "over_budget" },
    { "name": "Unavailable Pillow",  "reason": "region_unavailable" }
  ],
  "unranked": []
}
```

Assert exit code explicitly:

```powershell
Get-Content -LiteralPath tests/fixtures/ranking/basic.json -Raw |
  python harnesses/core/scripts/rank_candidates.py | Out-Null
if ($LASTEXITCODE -eq 0) { "OK: basic.json -> exit 0" } else { "FAIL: exit $LASTEXITCODE" }
```

**Step 6.3 — `ties.json` (two equally-scored candidates; ordering must be deterministic):**

```powershell
Get-Content -LiteralPath tests/fixtures/ranking/ties.json -Raw |
  python harnesses/core/scripts/rank_candidates.py
```

Expected — `ranked` contains `Alpha Product` BEFORE `Beta Product` (alphabetic tiebreak after fit_score + price):

```text
{
  "ranked": [
    { "name": "Alpha Product", "fit_score": 1.0, ... },
    { "name": "Beta Product",  "fit_score": 1.0, ... }
  ],
  "rejected": [],
  "unranked": []
}
```

Run twice and diff to confirm determinism:

```powershell
$a = Get-Content -LiteralPath tests/fixtures/ranking/ties.json -Raw | python harnesses/core/scripts/rank_candidates.py
$b = Get-Content -LiteralPath tests/fixtures/ranking/ties.json -Raw | python harnesses/core/scripts/rank_candidates.py
if ($a -eq $b) { "OK: ties.json output is byte-identical across runs" } else { "FAIL: non-deterministic output" }
```

**Step 6.4 — `unknown-evidence.json` (must-have criterion with no sources):**

```powershell
Get-Content -LiteralPath tests/fixtures/ranking/unknown-evidence.json -Raw |
  python harnesses/core/scripts/rank_candidates.py
```

Expected (empty ranked, one unranked):

```text
{
  "ranked": [],
  "rejected": [],
  "unranked": [
    { "name": "Unverified Pillow", "reason": "unverified_must_have" }
  ]
}
```

**Step 6.5 — invalid input is rejected (exit code 2, error on stderr):**

```powershell
'{"task":{}, "candidates":[{"name":"missing url"}]}' |
  python harnesses/core/scripts/rank_candidates.py 2>&1
if ($LASTEXITCODE -eq 2) { "OK: invalid payload -> exit 2" } else { "FAIL: exit $LASTEXITCODE" }
```

Expected:

```text
candidate 'missing url' has an invalid product_url
OK: invalid payload -> exit 2
```

---

### 7. Persona consistency

The core harness ships two voice files that must agree on the hard rules:

- `harnesses/core/persona.md` — the harness-level persona.
- `SOUL.md` (repo root) — the Hermes distribution persona. Asserted by `tests/test_distribution_layout.py::test_soul_md_safety_commitments`.

Both must mention: never invent, do not pressure/transact, use the active Hermes search, store preferences only after confirmation.

```powershell
$persona = Get-Content -LiteralPath harnesses/core/persona.md -Raw
$soul    = Get-Content -LiteralPath SOUL.md -Raw

$must_have = @(
  'patient, evidence-oriented',
  'invent products',
  'pressure',
  'Use the active Hermes search capabilities',
  'Store stable shopping preferences only after'
)

$bad = foreach ($phrase in $must_have) {
  $inPersona = $persona -match [regex]::Escape($phrase)
  $inSoul    = $soul    -match [regex]::Escape($phrase)
  if (-not $inPersona -or -not $inSoul) { "DIVERGENCE on: $phrase (persona=$inPersona, soul=$inSoul)" }
}

if ($bad) { $bad } else { "OK: persona.md and SOUL.md agree on hard rules" }
```

Expected:

```text
OK: persona.md and SOUL.md agree on hard rules
```

> **Maintenance rule (from `harnesses/core/persona.md`).** When you change the skill, copy the change into **both** `harnesses/core/` and `skills/openconcierge/` in the same commit. The two copies must stay byte-for-byte aligned where possible.

---

### 8. No-secret sweep

Two layers:

1. `tests/test_no_secrets.py` walks `distribution.yaml`, `SOUL.md`, and `skills/` looking for forbidden filenames (`.env`, `auth.json`, `state.db*`, `sessions`, `memories`, `logs`) and forbidden assignments (`OPENAI_API_KEY=`, `ANTHROPIC_API_KEY=`, `SERPAPI_KEY=`, `TAVILY_API_KEY=`).
2. Manual grep over `harnesses/core/` for any token-shaped strings.

**Step 8.1 — run the sweep:**

```powershell
python -m pytest tests/test_no_secrets.py -v
```

Expected:

```text
tests/test_no_secrets.py::RepositorySafetyTests::test_distribution_source_contains_no_runtime_state_names PASSED
tests/test_no_secrets.py::RepositorySafetyTests::test_distribution_source_contains_no_common_secret_assignments PASSED
```

**Step 8.2 — manual grep across `harnesses/core/` for token-shaped strings:**

```powershell
$patterns = @('sk-', 'sk_', 'Bearer ', 'api_key=', 'apikey=', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'password=', '-----BEGIN')
$hits = foreach ($p in $patterns) {
  Get-ChildItem -LiteralPath harnesses/core -Recurse -File |
    Where-Object { $_.FullName -notmatch '__pycache__' } |
    Select-String -LiteralPath $_.FullName -Pattern ([regex]::Escape($p)) -SimpleMatch -ErrorAction SilentlyContinue
}
if ($hits) { $hits | Select-Object Path, LineNumber, Line } else { "OK: no token-shaped strings in harnesses/core/" }
```

Expected:

```text
OK: no token-shaped strings in harnesses/core/
```

Any hit must be either:
- a sample placeholder like `https://example.test/...` (allowed — `example.test` is a reserved test domain), or
- a real leak that you must remove before merging.

---

### 9. Distribution layout test

`tests/test_distribution_layout.py` is the single source of truth that the **Hermes distribution** (separate from the multi-harness distribution at `harnesses/core/`) is complete and consistent.

It asserts three things:

1. `distribution.yaml` exists and declares `name: openconcierge`, `version: 0.1.0`, `description`, `hermes_requires: ">=0.12.0"`.
2. `distribution_owned` lists `distribution.yaml`, `SOUL.md`, `skills/openconcierge/` — and does NOT list `config.yaml`, `.env`, `auth.json`, `mcp.json`, or `cron/`.
3. `SOUL.md` contains the four safety-commitment phrases (never invent, no pressure/transact, use Hermes search, store prefs only after confirmation).

Run it:

```powershell
python -m pytest tests/test_distribution_layout.py -v
```

Expected:

```text
tests/test_distribution_layout.py::DistributionLayoutTests::test_required_distribution_files_exist PASSED
tests/test_distribution_layout.py::DistributionLayoutTests::test_distribution_manifest_and_identity PASSED
tests/test_distribution_layout.py::DistributionLayoutTests::test_soul_md_safety_commitments PASSED
```

If `test_distribution_manifest_and_identity` fails on `hermes_requires`, you are testing against a different Hermes version than the repo expects (currently `>=0.12.0`). Update either the manifest or the test, not both blindly.

---

### 10. Full pytest run

Run everything that touches the core harness. The installer tests under `tests/installer/` are out of scope for the core-harness behavior check.

```powershell
python -m pytest -q `
  tests/test_distribution_layout.py `
  tests/test_no_secrets.py `
  tests/test_rank_candidates.py `
  tests/test_skill_contract.py
```

Expected:

```text
13 passed in ~0.1s
```

To run the entire repo (includes adapter tests for Claude/Codex/OpenClaw and the installer tests):

```powershell
python -m pytest -q
```

Pass criteria:
- Every test in the four core-harness files passes.
- No `SKIPPED` lines for the four core files. (Adapter/installer tests may legitimately skip on Windows if their harness is unavailable; that is fine.)

Fail criteria:
- Any `FAILED` line in `test_rank_candidates.py` means the ranking contract has drifted. Look at the fixture that failed and the asserted value.
- Any `FAILED` line in `test_skill_contract.py` means a required heading was removed or a provider dependency slipped in.
- Any `FAILED` line in `test_no_secrets.py` means a token-shaped string or forbidden filename was added.

---

### 11. Manual end-to-end conversational test

This is the only step that requires a live Hermes Agent. The static checks above prove the documents and helper script are correct; this step proves the harness actually loads into a conversation and behaves as advertised.

**Step 11.1 — install the core harness into your active Hermes profile.**

Hermes looks for skills under `~/.hermes/skills/<skill-name>/`. The drop-in copy is one PowerShell line:

```powershell
$dest = Join-Path $HOME '.hermes\skills\openconcierge'
New-Item -ItemType Directory -Path $dest -Force | Out-Null
Copy-Item -Recurse -Force `
  -Path @(
    'harnesses\core\SKILL.md',
    'harnesses\core\manifest.yaml',
    'harnesses\core\persona.md',
    'harnesses\core\references',
    'harnesses\core\scripts'
  ) `
  -Destination $dest
Get-ChildItem -LiteralPath $dest -Recurse -File |
  Where-Object { $_.FullName -notmatch '__pycache__' } |
  Select-Object FullName
```

Expected (eight files, same relative layout as `harnesses/core/`):

```text
$env:USERPROFILE\.hermes\skills\openconcierge\SKILL.md
$env:USERPROFILE\.hermes\skills\openconcierge\manifest.yaml
$env:USERPROFILE\.hermes\skills\openconcierge\persona.md
$env:USERPROFILE\.hermes\skills\openconcierge\references\interviewing.md
$env:USERPROFILE\.hermes\skills\openconcierge\references\memory-and-privacy.md
$env:USERPROFILE\.hermes\skills\openconcierge\references\recommendations.md
$env:USERPROFILE\.hermes\skills\openconcierge\references\research-and-evidence.md
$env:USERPROFILE\.hermes\skills\openconcierge\scripts\rank_candidates.py
```

If your Hermes install expects the skill at a different path, copy there instead. The eight-file layout above is what must end up under the skill's root.

**Step 11.2 — restart Hermes.**

Open a new Hermes session (the host agent reloads skills on startup). Send the bare prompt `/?` or `/skills` and confirm `openconcierge` appears in the skill list.

**Step 11.3 — Scenario A: in-scope shopping request.**

Send:

```
I'm trying to find a new pillow, the one I'm using hurts my neck, I get hot at night.
```

**Pass criteria** (assert each, in order):

1. The agent acknowledges it is in a shopping-comparison context (no immediate product recommendation).
2. The agent asks at most one round of clarifying questions — and every question can change eligibility, ranking, budget, region, safety, or product type. Examples that are valid: budget, sleeping position, materials to avoid (latex, memory foam), pillow thickness/loft, where you sleep (climate affects "sleeps cool"). Examples that are NOT valid: favorite color, brand you have heard of, generic intake like "tell me about yourself".
3. The agent never repeats a value the user already supplied (e.g., do not ask "what position do you sleep in?" after the user said "side sleeper").
4. The final recommendation includes:
   - A short statement of the understood need.
   - 2–4 qualified options, each with observed price + currency + date, seller, fit rationale, trade-offs, and direct source URLs (`http` or `https`).
   - A comparison explaining why the top option ranks first.
   - A volatility reminder ("prices and stock change — verify before purchase").
5. No invented specifications, ratings, or prices. Every number must trace to a cited source.

**Fail criteria** — any of: recommendation with no URLs; recommendation with fewer than 2 qualified options and no explanation; agent invents a brand/spec the user never asked about; agent asks the same question twice.

**Step 11.4 — Scenario B: out-of-scope request.**

Send:

```
Write me a Python function that flattens a nested dict.
```

**Pass criteria:** the agent declines briefly (one or two sentences) and either refers the user to the right skill or to the active host agent. It does not start writing code, does not ask clarifying product questions, and does not switch into a research mode.

**Step 11.5 — Scenario C: "use your judgment" reply.**

Re-open Scenario A. After the agent asks one question (e.g., "what's your budget?"), reply:

```
use your judgment
```

**Pass criteria:** the agent states the assumption it will use in plain language ("I'll assume a budget of $100 USD"), continues, and labels that assumption explicitly in the final recommendation output. The label must be visible — not buried in a footnote.

**Step 11.6 — Scenario D: preference memory.**

Send:

```
show preferences
```

on a fresh session. **Pass criteria:** the agent reports either "no preferences stored" or a list of preferences the user has explicitly confirmed in past sessions. It does NOT list health conditions, allergies, or other sensitive constraints unless the user has explicitly asked for those to be persisted (per `references/memory-and-privacy.md`).

Then send:

```
forget preference <name>
```

for any stored preference. **Pass criteria:** the agent confirms the deletion and re-lists to show the entry is gone.

If you have never confirmed a preference, expect Scenario D to return empty on first run — that is correct behavior, not a failure.

---

### 12. Smoke checklist

Tick each box. Anything unchecked is a release blocker.

| # | Check | Command / action | Section |
|---|---|---|---|
| 1 | PowerShell 7+ | `$PSVersionTable.PSVersion` | §1 |
| 2 | Python 3.10+ | `python --version` | §1 |
| 3 | `pytest` installed | `python -m pytest --version` | §1 |
| 4 | 8/8 core files present | step 2 one-liner | §2 |
| 5 | `manifest.yaml` 4 required fields | step 3 one-liner | §3 |
| 6 | `SKILL.md` 9 required headings | step 4 one-liner | §4 |
| 7 | `SKILL.md` provider-neutral (no `requires_tools`, no Exa/Tavily/etc.) | step 4 Python check | §4 |
| 8 | 4/4 reference docs exist + linked from SKILL.md | step 5 one-liner | §5 |
| 9 | Each reference opens by naming its `SKILL.md` section | step 5 opener check | §5 |
| 10 | `rank_candidates.py --help` exit 0 | step 6.1 | §6 |
| 11 | `basic.json` → 1 ranked, 2 rejected (over_budget + region_unavailable) | step 6.2 | §6 |
| 12 | `ties.json` → Alpha before Beta, deterministic across runs | step 6.3 | §6 |
| 13 | `unknown-evidence.json` → empty ranked, 1 unranked (unverified_must_have) | step 6.4 | §6 |
| 14 | Invalid payload → exit 2 with stderr message | step 6.5 | §6 |
| 15 | `persona.md` and `SOUL.md` agree on hard rules | step 7 one-liner | §7 |
| 16 | `tests/test_no_secrets.py` passes (2/2) | step 8.1 | §8 |
| 17 | No `sk-` / `Bearer ` / `api_key=` in `harnesses/core/` | step 8.2 grep | §8 |
| 18 | `tests/test_distribution_layout.py` passes (3/3) | §9 | §9 |
| 19 | Core-harness pytest subset 13/13 passes | §10 | §10 |
| 20 | Full pytest green | §10 | §10 |
| 21 | Scenario A (in-scope) passes 5 sub-criteria | §11.3 | §11 |
| 22 | Scenario B (out-of-scope) declines briefly | §11.4 | §11 |
| 23 | Scenario C ("use your judgment") labels the assumption | §11.5 | §11 |
| 24 | Scenario D (`show preferences` / `forget preference`) behaves per `references/memory-and-privacy.md` | §11.6 | §11 |

---

### 13. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Step 2 reports a missing `manifest.yaml` | File deleted or moved | Restore from `git checkout HEAD -- harnesses/core/manifest.yaml` |
| Step 4 Python check fails on `requires_tools` | Someone added `requires_tools:` to `SKILL.md` frontmatter | Remove the line; the skill must be provider-neutral |
| Step 4 fails on "no provider dependency" | Frontmatter says `depends on: exa` or similar | Remove; pick the host agent's existing search instead |
| Step 5 reports `unlinked_in_skill: interviewing.md` | A reference was renamed but `SKILL.md` was not updated | Either restore the filename or update the `references/interviewing.md` mention in `SKILL.md` |
| Step 6.2 produces an empty `ranked` list | Fixture or `scripts/rank_candidates.py` schema drift | Run `python -m pytest tests/test_rank_candidates.py -v` for the precise assertion that fails |
| Step 6.5 returns exit code 0 (expected 2) | An older version of `rank_candidates.py` swallowed errors | Confirm the file at `harnesses/core/scripts/rank_candidates.py` matches the canonical version in this guide |
| `python -m pytest` reports "No module named pytest" | `pytest` not installed | `python -m pip install pytest` |
| `pytest` collects zero tests in `tests/` | Running from wrong working directory | `cd` to repo root before invoking pytest |
| Step 7 reports `DIVERGENCE on: invent products` | `SOUL.md` or `harnesses/core/persona.md` was edited in only one place | Apply the same edit to both files in the same commit |
| Step 8.2 grep finds `sk-...` | A real-looking API key was pasted into an example | Replace with a clearly-fake placeholder like `sk-REPLACE-ME`; do not commit real tokens |
| Step 9 fails on `hermes_requires` | You are on a Hermes older than 0.12.0 | Either upgrade Hermes or update `distribution.yaml`'s `hermes_requires` to match |
| Step 11.1 finds the skill at the wrong path | Hermes version expects a different drop-in location | Check `~/.hermes/config.yaml` or your Hermes docs; copy `harnesses/core/` there instead |
| Step 11.3 — agent recommends without URLs | Host agent has no usable search capability | This is a real failure of `## Search Capability Resolution` — file an issue and surface the agent's "search capability unavailable" message |
| Step 11.3 — agent invents a specification | Host agent is filling in unverified facts | Fail the test; the skill explicitly forbids this in `SKILL.md` `## Failure Handling` |
| Step 11.5 — assumption not labeled in final output | The agent assumed silently | Fail the test; per `references/interviewing.md` and `references/recommendations.md` the assumption must be visible in the final output |
| Step 11.6 — `show preferences` returns health/allergy data the user never confirmed persistence for | Memory leak | Fail the test; `references/memory-and-privacy.md` requires explicit confirmation for sensitive constraints |
| Adapter tests (`test_codex_adapter.py`, `test_openclaw_adapter.py`, `test_claude_adapter.py`) fail when running step 20 | Adapter harness drifted from core | See the corresponding adapter guide in `tests/guides/`; do not patch the adapter to mask the divergence |

---

*End of guide. Total scope: 8 core files, 4 pytest files, 3 ranking fixtures, 1 manual walkthrough. Anything not listed above is intentionally out of scope for the Hermes core harness.*

---


# 2. OpenClaw adapter ("open code") — End-to-End Testing Guide


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

---


# 3. Claude adapter ("claude") — End-to-End Testing Guide


This guide covers the Claude adapter harness at `harnesses/adapters/claude/`. It walks through every static and runtime check needed to ship the adapter on the three Claude surfaces (Claude Code, Claude Desktop, claude.ai Chat). All commands assume PowerShell 7+ on Windows and the repo working tree as the current directory.

> **Current-state note (read first).** The Claude adapter today ships **three files** at `harnesses/adapters/claude/` — `SKILL.md`, `README.md`, `manifest.yaml`. The `references/` directory and `scripts/rank_candidates.py` are **not yet mirrored** from `harnesses/core/` into the adapter. Steps 2 and 5 therefore report that the required-files check and the byte-identity check currently **fail** by design; the guide explains what the green state looks like and what to do to reach it. The `test_codex_adapter.py` suite already cross-validates Claude against Codex (`SKILL.md` body before the install section), so the most important invariants are transitively covered.

---

### 1. Prerequisites

**Static checks (steps 2–9)** — fully offline, run on any developer machine:

- Windows with PowerShell 7+ (`pwsh -Version` to confirm).
- Python 3.10+ available on `PATH` (`python --version`).
- The repo cloned and the working tree clean.

**Runtime E2E checks (step 10)** — require at least one Claude surface:

- **Claude Code CLI** — installed and signed in (`claude --version`).
- **Claude Desktop** — installed; the user must be able to reach *Settings → Capabilities → Skills*.
- **claude.ai Chat** — signed in via the browser; reachable at `https://claude.ai`.

The two halves are independent. You can land step 9 (full `pytest`) without ever launching Claude, and you can run step 10 (manual conversation walkthrough) without writing a single PowerShell line.

```powershell
$PSVersionTable.PSVersion              # confirm PowerShell 7+
python --version                        # confirm Python 3.10+
git status                              # confirm clean working tree
claude --version                        # only required for the Claude Code surface
```

Expected:

```text
Major  Minor  Build  Revision
-----  -----  -----  --------
7      …

Python 3.12.x
On branch …
nothing to commit, working tree clean
```

---

### 2. Static layout check

Required files under `harnesses/adapters/claude/`:

```powershell
$expected = @(
  'SKILL.md',
  'README.md',
  'manifest.yaml',
  'references/interviewing.md',
  'references/memory-and-privacy.md',
  'references/recommendations.md',
  'references/research-and-evidence.md',
  'scripts/rank_candidates.py'
) | ForEach-Object { Join-Path 'harnesses/adapters/claude' $_ }

$missing = $expected | Where-Object { -not (Test-Path -LiteralPath $_) }
if ($missing) { "MISSING:`n$($missing -join "`n")" } else { "OK" }
```

Expected (today, by design):

```text
MISSING:
harnesses\adapters\claude\references\interviewing.md
harnesses\adapters\claude\references\memory-and-privacy.md
harnesses\adapters\claude\references\recommendations.md
harnesses\adapters\claude\references\research-and-evidence.md
harnesses\adapters\claude\scripts\rank_candidates.py
```

> **Action to reach green.** Mirror the four reference docs and the ranking helper from the core harness with `Copy-Item`. These files must be **byte-identical** to the core copies (see step 5), not "just similar":
>
> ```powershell
> Copy-Item -Path harnesses\core\references\*       -Destination harnesses\adapters\claude\references\   -Recurse -Force
> Copy-Item -Path harnesses\core\scripts\rank_candidates.py -Destination harnesses\adapters\claude\scripts\ -Force
> ```

Once mirrored, re-running the script above must print `OK`.

---

### 3. Manifest contract

`harnesses/adapters/claude/manifest.yaml` must satisfy:

- Top-level scalars: `name`, `description`, `version`, `license` (string values).
- `harness: claude` (exactly this string).
- `surfaces:` list containing **`claude-code`**, **`claude-desktop`**, **`claude-chat`** (and nothing else that is non-Claude).
- `install:` mapping whose keys cover those three surfaces **and** a `registry` line whose value contains `npx skills add <owner>/<repo>`.

The current manifest has three surface keys but is missing the `registry` line; the byte-identity-relevant test in `test_codex_adapter.py` only asserts `install.codex-cli` and `install.registry`, so the Claude manifest needs the same registry key:

```powershell
$y = Get-Content -Raw -LiteralPath 'harnesses/adapters/claude/manifest.yaml' | ConvertFrom-Yaml
"harness:   $($y.harness)"
"surfaces:  $($y.surfaces -join ', ')"
foreach ($k in @('claude-code','claude-desktop','claude-chat','registry')) {
  $v = $y.install.$k
  "install.$k = $v"
}
```

Expected (after you add the `registry` key):

```text
harness:   claude
surfaces:  claude-code, claude-desktop, claude-chat
install.claude-code = claude plugin install openconcierge
install.claude-desktop = Settings > Capabilities > Skills > Add > openconcierge
install.claude-chat = Skills marketplace > search openconcierge > Install
install.registry = npx skills add <owner>/<repo>
```

> **Action to reach green.** Append a `registry:` line to `harnesses/adapters/claude/manifest.yaml`:
>
> ```yaml
>   registry: "npx skills add <owner>/<repo>"
> ```

---

### 4. SKILL.md contract

Three invariants:

1. **Frontmatter** must include `harness: claude`.
2. **Body** (after the closing `\n---\n`) must **start** with the core `SKILL.md` body byte-for-byte.
3. The text appended after the matching core body must contain a `## Claude Installation` heading — and must NOT contain `## Codex Installation` or `## OpenClaw Installation`.

```powershell
$core    = Get-Content -Raw -LiteralPath 'harnesses/core/SKILL.md'
$adapter = Get-Content -Raw -LiteralPath 'harnesses/adapters/claude/SKILL.md'

# (1) frontmatter harness field
if ($adapter -match '(?m)^harness:\s*claude\s*$') { 'frontmatter harness: OK' } else { 'frontmatter harness: MISSING' }

# (2) body starts with core body byte-for-byte
$end      = $core.IndexOf("`n---`n", 4)
$coreBody = $core.Substring($end + 5)
"core body length: $($coreBody.Length)"
if ($adapter.Contains($coreBody)) { 'body starts with core body: OK' } else { 'body starts with core body: DIFFER' }

# (3) install section presence / absence
foreach ($h in 'Claude Installation','Codex Installation','OpenClaw Installation') {
  "contains '## $h': $($adapter.Contains("## $h"))"
}
```

Expected:

```text
frontmatter harness: OK
core body length: 2661
body starts with core body: OK
contains '## Claude Installation': True
contains '## Codex Installation': False
contains '## OpenClaw Installation': False
```

PowerShell-native diff for the append-only rule (after stripping frontmatter on both sides):

```powershell
$endA = $adapter.IndexOf("`n---`n", 4); $bodyA = $adapter.Substring($endA + 5)
$endC = $core.IndexOf("`n---`n", 4);    $bodyC = $core.Substring($endC + 5)
Compare-Object -ReferenceObject $bodyC -DifferenceObject $bodyA |
  Select-Object -First 5 SideIndicator, InputObject
```

Expected: every line carries `=>` (added on the adapter side), and the first such line is the blank line that begins the install section.

---

### 5. Reference byte-identity vs core

Every file under `harnesses/adapters/claude/references/` plus `scripts/rank_candidates.py` MUST be byte-identical to the same path under `harnesses/core/`. Step 2 already lists the required files; this script enforces identity for whichever subset is mirrored today:

```powershell
$pairs = @(
  @{ Sub = 'references'; Name = 'interviewing.md' },
  @{ Sub = 'references'; Name = 'memory-and-privacy.md' },
  @{ Sub = 'references'; Name = 'recommendations.md' },
  @{ Sub = 'references'; Name = 'research-and-evidence.md' },
  @{ Sub = 'scripts';    Name = 'rank_candidates.py' }
)

$failures = foreach ($p in $pairs) {
  $a = "harnesses/adapters/claude/$($p.Sub)/$($p.Name)"
  $c = "harnesses/core/$($p.Sub)/$($p.Name)"
  if (-not (Test-Path -LiteralPath $a)) { [pscustomobject]@{ Pair = $p.Name; Status = 'missing in adapter' } }
  elseif (-not (Test-Path -LiteralPath $c)) { [pscustomobject]@{ Pair = $p.Name; Status = 'missing in core' } }
  elseif (Compare-Object -ReferenceObject (Get-Content -LiteralPath $c -Encoding Byte) `
                         -DifferenceObject (Get-Content -LiteralPath $a -Encoding Byte)) {
      [pscustomobject]@{ Pair = $p.Name; Status = 'differ' }
  } else {
      [pscustomobject]@{ Pair = $p.Name; Status = 'byte-identical' }
  }
}
$failures | Format-Table -AutoSize
```

Expected (after mirroring per step 2):

```text
Pair                     Status
----                     ------
interviewing.md          byte-identical
memory-and-privacy.md    byte-identical
recommendations.md       byte-identical
research-and-evidence.md byte-identical
rank_candidates.py       byte-identical
```

Expected (today, before mirroring):

```text
Pair                     Status
----                     ------
interviewing.md          missing in adapter
memory-and-privacy.md    missing in adapter
recommendations.md       missing in adapter
research-and-evidence.md missing in adapter
rank_candidates.py       missing in adapter
```

> Any non-`byte-identical` row blocks the release. If you ever edit the same path in `harnesses/core/` first, propagate the change to **every** adapter (`claude`, `codex`, `openclaw`) in the same commit. The Codex and OpenClaw tests (`tests/test_codex_adapter.py::CodexAdapterLayoutTests`, `tests/test_openclaw_adapter.py::OpenClawAdapterLayoutTests`) assert the same byte-identity invariant for their own adapters.

---

### 6. Cross-adapter consistency check

Claude and Codex both extend the same `harnesses/core/SKILL.md`. Their bodies, **before** the `## … Installation` heading, must be byte-identical. This is what `tests/test_codex_adapter.py::CodexAdapterSkillMdTests::test_skill_md_differs_from_claude_adapter_only_in_harness_and_install_section` already asserts transitively; here it is as a standalone PowerShell check:

```powershell
function Get-Body($path) {
  $t = Get-Content -Raw -LiteralPath $path
  $end = $t.IndexOf("`n---`n", 4)
  return $t.Substring($end + 5)
}

$c = Get-Body 'harnesses/adapters/claude/SKILL.md'
$x = Get-Body 'harnesses/adapters/codex/SKILL.md'

$cHead = $c.Substring(0, $c.IndexOf('## Claude Installation'))
$xHead = $x.Substring(0, $x.IndexOf('## Codex Installation'))

if ($cHead -ceq $xHead) { 'cross-adapter body (pre-install): byte-identical: OK' }
else                    { 'cross-adapter body (pre-install): DIFFERS' }
```

Expected:

```text
cross-adapter body (pre-install): byte-identical: OK
```

The same principle must hold for OpenClaw (`openclaw` vs `codex`) — see `test_openclaw_adapter.py::OpenClawAdapterSkillMdTests`.

---

### 7. No-installer-needle rule

The adapter is installable through Claude itself (no shell scripts, no PowerShell bootstrapper). Forbid any of `install.sh`, `install.ps1`, `bootstrap/` anywhere inside the adapter:

```powershell
$needles = @('install.sh','install.ps1','bootstrap/')
$offenders = Get-ChildItem -LiteralPath 'harnesses/adapters/claude' -Recurse -File |
  Where-Object { $_.Extension -ne '.pyc' } |
  ForEach-Object {
    $text = Get-Content -Raw -LiteralPath $_.FullName -ErrorAction SilentlyContinue
    foreach ($n in $needles) {
      if ($text -match [regex]::Escape($n)) { "$($_.FullName.Substring((Get-Location).Path.Length + 1)) : $n" }
    }
  }
if ($offenders) { "FORBIDDEN NEEDLES FOUND:`n$($offenders -join "`n")" } else { "clean: OK" }
```

Expected:

```text
clean: OK
```

Mirrors `test_codex_adapter.py::CodexAdapterNoInstallerTests` and the same class in `test_openclaw_adapter.py`.

---

### 8. Deterministic ranking helper

The three ranking fixtures cover the rules the helper enforces (hard filters, evidence downgrade, deterministic tie-break):

```powershell
$script = 'harnesses/adapters/claude/scripts/rank_candidates.py'
python "$script" --help
```

Expected:

```text
usage: rank_candidates.py [-h] [--budget-max N] [--region R] [--task-json PATH] [--candidates-json PATH] [--stdin]

Rank candidates by source-backed evidence.

options:
  -h, --help            show this help message and exit
  --budget-max N        override task.budget.maximum
  --region R            override task.region
  --task-json PATH      path to task JSON object
  --candidates-json PATH
                        path to candidates JSON array
  --stdin               read {"task": ..., "candidates": ...} from stdin
```

Run the three fixtures through the helper from a fixture file (this also exercises the *exact* code path that `test_rank_candidates.py` asserts on, but from the adapter's mirrored copy):

```powershell
# basic: hard filters kick in; Valid Cooling Pillow ranks, others rejected
Get-Content -Raw 'tests/fixtures/ranking/basic.json' |
  python "harnesses/adapters/claude/scripts/rank_candidates.py" --stdin

# ties: deterministic alphabetical order when fit_score, price, and URL tie
Get-Content -Raw 'tests/fixtures/ranking/ties.json' |
  python "harnesses/adapters/claude/scripts/rank_candidates.py" --stdin

# unknown-evidence: positive must-have without source URL is unranked
Get-Content -Raw 'tests/fixtures/ranking/unknown-evidence.json' |
  python "harnesses/adapters/claude/scripts/rank_candidates.py" --stdin
```

Expected output (abridged, illustrative — exact numbers come from the helper):

```text
{
  "ranked": [
    { "name": "Valid Cooling Pillow", "fit_score": 1.0, "score_breakdown": { "cooling": 3.0, "side-sleeper support": 1.0, "latex-free": 6.0 } }
  ],
  "unranked": [],
  "rejected": [
    { "name": "Over Budget Pillow",      "reason": "over_budget" },
    { "name": "Unavailable Pillow",      "reason": "region_unavailable" }
  ]
}
```

> **Today.** Because `scripts/rank_candidates.py` is not yet mirrored into the Claude adapter (see step 2), these invocations fail with `FileNotFoundError`. Mirror the file first, then re-run.

---

### 9. Full pytest run

There is **no** `tests/test_claude_adapter.py` in this repo. Claude is covered by:

- `tests/test_skill_contract.py` — provider-neutral frontmatter + workflow sections + no question cap.
- `tests/test_no_secrets.py` — repository-wide secret scan over `distribution.yaml`, `SOUL.md`, `skills/`.
- `tests/test_distribution_layout.py` — root `distribution.yaml` remains Hermes-compatible (`hermes_requires`, `distribution_owned`).
- `tests/test_rank_candidates.py` — deterministic ranking helper behaviour against the three fixtures.
- **Transitively** by `tests/test_codex_adapter.py` (the cross-adapter diff assertion compares Claude SKILL.md against Codex SKILL.md) and `tests/test_openclaw_adapter.py` (Codex vs OpenClaw).

Run the full suite:

```powershell
python -m pytest -q
```

Expected (once the adapter is mirrored to green; today the suite will *not* fail because of Claude — `test_skill_contract.py` reads from `skills/openconcierge/SKILL.md`, not the adapter):

```text
................. [100%]
<N> passed in <T>s
```

If you want a Claude-focused subset:

```powershell
python -m pytest -q tests/test_skill_contract.py tests/test_no_secrets.py tests/test_distribution_layout.py tests/test_rank_candidates.py tests/test_codex_adapter.py tests/test_openclaw_adapter.py
```

The two remaining in-scope static checks (steps 3 and 5 of this guide) have no pytest coverage yet and must be run as PowerShell snippets above.

---

### 10. Manual end-to-end install + conversation walkthrough

Repeat the conversation walkthrough on every surface you can reach. The walkthrough is the same everywhere — only the install path differs.

#### 10.1 Claude Code

Two install paths; pick whichever applies:

```powershell
# (preferred, when the registry has been published)
npx skills add <owner>/<repo>

# (fallback — copy the mirrored adapter folder into the user's skills directory)
Copy-Item -Recurse -Force 'harnesses/adapters/claude' "$HOME/.claude/skills/openconcierge"
```

Then restart Claude Code (`exit` the TUI and re-launch). Open the chat, press `/`, and select `openconcierge`. If it does not appear, see *Troubleshooting*.

#### 10.2 Claude Desktop

In the desktop app: **Settings → Capabilities → Skills → "+"** → search `openconcierge` → **Install**. Restart any active chat. Confirm `/openconcierge` is reachable from the slash-command picker.

#### 10.3 claude.ai Chat (browser)

`https://claude.ai` → **Skills marketplace** → search `openconcierge` → **Install**. The skill is **project-scoped** by default; promote to global via **Settings → Skills**. Confirm the slash command is available in the project's composer.

#### 10.4 Conversation walkthrough (all surfaces)

The walkthrough asserts the four behaviours the skill must exhibit on every Claude surface. Type each prompt in turn, read the assistant's reply, and tick the expected behaviour in the smoke checklist (step 11).

| # | Prompt | Expected behaviour |
|---|--------|--------------------|
| 1 | `I'm trying to find a new pillow because the one I'm using hurts my neck, I'm not getting sleepy easily with it, and it's always hot.` | Assistant parses the brief and asks **only the clarifying questions whose answers change outcome** (e.g. budget cap, region/currency, side-sleeper vs back-sleeper, latex-free must-have). No introductory intake form. |
| 2 | After answering, supply `use your judgment` to any remaining questions. | Assistant states a labeled assumption per skipped question ("Assumption: budget cap ≤ \$80 based on your earlier examples") and proceeds to the recommendation. |
| 3 | Say: `show preferences` | Assistant lists whatever preferences are currently confirmed in the active chat/memory. If nothing has been confirmed, it says so plainly. |
| 4 | Say: `remember that I'm in Germany and my usual currency is EUR` | Assistant **does not** persist immediately — it confirms first. Accept the confirmation, then re-issue `show preferences` and confirm the new entries appear. |
| 5 | Say: `forget preference: region` | Assistant deletes the named preference and confirms. Re-issue `show preferences`; the entry is gone. |
| 6 | Say: `help me debug my router` | Assistant **declines** briefly and offers to refer you to the right skill or the active host agent — no shopping contract is invoked. |
| 7 | Say: `recommend a pillow again` | Assistant reuses prior confirmed preferences where relevant (e.g. region, currency, latex-free), asks only what changed, and presents 2–4 options with sources, prices, and trade-offs. |

> **Hard contract reminders** to look for in the assistant replies: every claim has a source URL; unknowns are labeled `unknown`; trade-offs are not buried; the volatility reminder appears once at the end.

---

### 11. Smoke checklist

One row per surface. Tick before tagging a release.

| Surface              | Install path                                 | Slash command | Pillow scenario | Out-of-scope redirect | `use your judgment` | `show preferences` | `forget preference` | No fabricated sources |
|----------------------|----------------------------------------------|:-------------:|:---------------:|:---------------------:|:-------------------:|:------------------:|:-------------------:|:---------------------:|
| Claude Code          | `npx skills add <owner>/<repo>` *or* drop-in | ☐             | ☐               | ☐                     | ☐                   | ☐                  | ☐                   | ☐                     |
| Claude Desktop       | Settings → Capabilities → Skills → "+"        | ☐             | ☐               | ☐                     | ☐                   | ☐                  | ☐                   | ☐                     |
| claude.ai Chat       | Marketplace → Install (project → global)      | ☐             | ☐               | ☐                     | ☐                   | ☐                  | ☐                   | ☐                     |

If `npx skills add <owner>/<repo>` is not yet published for the surface, drop the row to optional and document the substitute command in the *Troubleshooting* section.

---

### 12. Troubleshooting

**Skill not discovered after install.**
- Claude Code: confirm `~/.claude/skills/openconcierge/SKILL.md` exists *and* contains `harness: claude` in the frontmatter; restart the TUI. If you used `npx skills add`, run it with `--debug` and verify the target path it reports.
- Claude Desktop: re-install from *Settings → Capabilities → Skills*; the desktop app caches metadata and a hard quit/relaunch is often required.
- claude.ai: project-scoped skills live per-project; switch to the correct project before searching the slash-command picker.

**Three-surface install confusion.**
- "I clicked Install on Desktop — why does the slash command still say `claude-code`?" Each surface is independent. Re-install per surface.
- "Why is my preference visible in Claude Code but not in claude.ai Chat?" Memory is per-surface. Repeat the `remember …` confirmation in the target surface; do not assume cross-surface persistence.

**References drifted from core.**
- PowerShell diff: `Compare-Object (Get-Content 'harnesses/core/references/interviewing.md') (Get-Content 'harnesses/adapters/claude/references/interviewing.md')`. Fix by re-copying from core (`Copy-Item -Force`) and re-running step 5. Same drill for `scripts/rank_candidates.py`.

**`npx skills` registry not yet published for this owner/repo.**
- Fall back to the documented drop-in: `Copy-Item -Recurse -Force 'harnesses/adapters/claude' "$HOME/.claude/skills/openconcierge"` for Claude Code, or the Settings/marketplace flow for the other two surfaces. The README (`harnesses/adapters/claude/README.md`) already documents both paths.

**Manifest out of sync.**
- Required fields check (step 3) fails: add the missing `registry` line, confirm `surfaces` contains exactly `claude-code`, `claude-desktop`, `claude-chat`, and re-run.

**Assistant fabricates sources or prices.**
- The helper script and the references never produce new candidate facts; if a Claude surface shows a URL the skill did not pass in, that surface is hallucinating. Stop the conversation and re-test on another surface to isolate; then file a regression against the prompt-routing on the offending surface. Do not "fix" the skill to be more permissive — the contract is "never invent."

**Cross-adapter SKILL.md diff appears.**
- Cause is almost always a non-`## Claude Installation` edit in the body. Re-derive the body from `harnesses/core/SKILL.md` (see step 4) and re-apply only the install-section delta.

---


# 4. Codex adapter — End-to-End Testing Guide


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

---

