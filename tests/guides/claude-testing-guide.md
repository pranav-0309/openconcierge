## Claude Adapter — End-to-End Testing Guide

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
