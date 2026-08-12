## Hermes Harness — End-to-End Testing Guide

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
