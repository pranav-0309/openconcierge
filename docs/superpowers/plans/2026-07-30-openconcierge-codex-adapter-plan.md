# OpenConcierge Codex Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill in the existing `harnesses/adapters/codex/` stub so OpenConcierge is available to Codex CLI users as a droppable skill folder (no installer) and to a Codex-compatible skills registry.

**Architecture:** Mirror the existing `harnesses/adapters/claude/` pattern. Behavior content (`SKILL.md` body, `references/*.md`, `scripts/rank_candidates.py`) is byte-identical with `harnesses/core/`. The adapter adds three Codex-specific files (`SKILL.md` with `harness: codex` and an appended install section, `manifest.yaml`, `README.md`). The adapter folder is self-contained — `references/` and `scripts/` are copied into it so a drop-in folder is portable.

**Tech Stack:** Python 3.12 (stdlib only — no third-party deps added), Pytest + `unittest.TestCase` (existing project convention), PowerShell on Windows / Bash on macOS/Linux for copy operations.

---

## File Structure

### Files to create

| Path | Responsibility |
|---|---|
| `harnesses/adapters/codex/SKILL.md` | Byte-identical body to `harnesses/core/SKILL.md` + `harness: codex` frontmatter line + appended `## Codex Installation` section |
| `harnesses/adapters/codex/README.md` | User-facing install + usage docs (overwrites existing stub) |
| `harnesses/adapters/codex/manifest.yaml` | Declares `surfaces: [codex-cli]`, drop-in path, and registry install command |
| `harnesses/adapters/codex/references/interviewing.md` | Byte-identical copy of `harnesses/core/references/interviewing.md` |
| `harnesses/adapters/codex/references/memory-and-privacy.md` | Byte-identical copy of `harnesses/core/references/memory-and-privacy.md` |
| `harnesses/adapters/codex/references/recommendations.md` | Byte-identical copy of `harnesses/core/references/recommendations.md` |
| `harnesses/adapters/codex/references/research-and-evidence.md` | Byte-identical copy of `harnesses/core/references/research-and-evidence.md` |
| `harnesses/adapters/codex/scripts/rank_candidates.py` | Byte-identical copy of `harnesses/core/scripts/rank_candidates.py` |
| `tests/test_codex_adapter.py` | Structural assertions: folder shape, byte-equivalence, manifest parses, no installer references, drop-in portability |

### Files to modify

| Path | Change |
|---|---|
| `harnesses/adapters/codex/README.md` | Overwrite the existing 7-line stub README with the real README |

### Files explicitly NOT touched

- `harnesses/core/` — canonical content stays single-sourced
- `harnesses/adapters/claude/` — sibling adapter is unchanged
- `skills/openconcierge/` — Hermes distribution is unchanged
- `bootstrap/` — Hermes installer is unchanged; Codex has no installer per spec
- `.claude-plugin/marketplace.json` — Codex doesn't go through skills.sh; leaving alone
- `distribution.yaml` — Hermes-specific, unchanged

---

## Task 1: Confirm preconditions

**Files:** none

- [ ] **Step 1: Verify `harnesses/core/` has the expected files**

Run from repo root:

```bash
ls harnesses/core/
ls harnesses/core/references/
ls harnesses/core/scripts/
```

Expected output: `manifest.yaml`, `persona.md`, `SKILL.md` in `harnesses/core/`; 4 `.md` files in `harnesses/core/references/`; `rank_candidates.py` in `harnesses/core/scripts/`.

If any file is missing, stop and resolve before proceeding — the spec requires byte-identical copies of these.

- [ ] **Step 2: Verify the existing Codex stub**

Run from repo root:

```bash
ls harnesses/adapters/codex/
```

Expected output: a single `README.md` (the stub). The folder currently contains nothing else.

- [ ] **Step 3: Verify pytest discovers existing tests**

Run from repo root:

```bash
python -m pytest tests/ --collect-only
```

Expected output: 52 collected tests (or whatever the current count is; the point is that pytest works and tests collect).

If pytest errors, fix the environment before proceeding.

- [ ] **Step 4: Commit baseline check (no changes yet)**

```bash
git status
```

Expected: clean tree or only the spec doc we just committed. If anything else is dirty, commit or stash before proceeding.

---

## Task 2: Write failing tests for Codex adapter structure

**Files:**
- Create: `tests/test_codex_adapter.py`

- [ ] **Step 1: Create the test file with all five structural tests**

Create `tests/test_codex_adapter.py` with this exact content:

```python
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
CODEX = ROOT / "harnesses" / "adapters" / "codex"
CORE = ROOT / "harnesses" / "core"


class CodexAdapterLayoutTests(unittest.TestCase):
    def test_required_files_exist(self):
        expected = (
            CODEX / "SKILL.md",
            CODEX / "README.md",
            CODEX / "manifest.yaml",
            CODEX / "references" / "interviewing.md",
            CODEX / "references" / "memory-and-privacy.md",
            CODEX / "references" / "recommendations.md",
            CODEX / "references" / "research-and-evidence.md",
            CODEX / "scripts" / "rank_candidates.py",
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
            adapter_path = CODEX / subdir / name
            core_path = CORE / subdir / name
            self.assertTrue(adapter_path.is_file(), f"missing {adapter_path}")
            self.assertTrue(core_path.is_file(), f"missing {core_path}")
            self.assertEqual(
                adapter_path.read_bytes(),
                core_path.read_bytes(),
                f"{adapter_path.relative_to(ROOT)} must be byte-identical to "
                f"{core_path.relative_to(ROOT)}",
            )


class CodexAdapterSkillMdTests(unittest.TestCase):
    def test_skill_md_body_matches_core_except_install_section(self):
        core_text = (CORE / "SKILL.md").read_text(encoding="utf-8")
        adapter_text = (CODEX / "SKILL.md").read_text(encoding="utf-8")

        self.assertTrue(adapter_text.startswith("---\n"), "adapter SKILL.md must start with YAML frontmatter")
        self.assertRegex(adapter_text, r"(?m)^harness:\s*codex\s*$")

        core_body = self._strip_frontmatter(core_text)
        adapter_body = self._strip_frontmatter(adapter_text)

        self.assertTrue(
            adapter_body.startswith(core_body),
            "adapter SKILL.md body (after frontmatter) must begin with the core SKILL.md body byte-for-byte",
        )

        appended = adapter_body[len(core_body):]
        self.assertIn("## Codex Installation", appended, "adapter must append a '## Codex Installation' section")

    def test_skill_md_differs_from_claude_adapter_only_in_harness_and_install_section(self):
        claude_skill = ROOT / "harnesses" / "adapters" / "claude" / "SKILL.md"
        self.assertTrue(claude_skill.is_file(), "claude adapter SKILL.md must exist (sanity)")
        self.assertTrue((CODEX / "SKILL.md").is_file(), "codex adapter SKILL.md must exist")

        claude_text = claude_skill.read_text(encoding="utf-8")
        codex_text = (CODEX / "SKILL.md").read_text(encoding="utf-8")

        self.assertRegex(claude_text, r"(?m)^harness:\s*claude\s*$")
        self.assertIn("## Claude Installation", claude_text)
        self.assertRegex(codex_text, r"(?m)^harness:\s*codex\s*$")
        self.assertIn("## Codex Installation", codex_text)

        self.assertNotIn("## Claude Installation", codex_text, "codex adapter must not contain the Claude install section")
        self.assertNotIn("## Codex Installation", claude_text, "claude adapter must not contain the Codex install section")

        claude_body = self._strip_frontmatter(claude_text)
        codex_body = self._strip_frontmatter(codex_text)
        codex_install_idx = codex_body.index("## Codex Installation")
        claude_install_idx = claude_body.index("## Claude Installation")

        self.assertEqual(
            codex_body[:codex_install_idx],
            claude_body[:claude_install_idx],
            "the portion of the SKILL.md body BEFORE the install section must be byte-identical between claude and codex adapters",
        )

    @staticmethod
    def _strip_frontmatter(text):
        end = text.find("\n---\n", 4)
        if end == -1:
            raise AssertionError("missing closing '---' on YAML frontmatter")
        return text[end + 5 :]


class CodexAdapterManifestTests(unittest.TestCase):
    def test_manifest_yaml_parses_with_expected_fields(self):
        manifest_path = CODEX / "manifest.yaml"
        self.assertTrue(manifest_path.is_file(), "manifest.yaml must exist")
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "openconcierge")
        self.assertEqual(manifest["harness"], "codex")
        self.assertIn("version", manifest)
        self.assertIn("description", manifest)
        self.assertIn("license", manifest)
        self.assertEqual(manifest["surfaces"], ["codex-cli"])
        self.assertIn("install", manifest)
        self.assertIn("codex-cli", manifest["install"])
        self.assertIn("registry", manifest["install"])


class CodexAdapterNoInstallerTests(unittest.TestCase):
    FORBIDDEN_NEEDLES = ("install.sh", "install.ps1", "bootstrap/")

    def test_no_installer_references_in_adapter(self):
        offenders = []
        for path in CODEX.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix in {".pyc"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for needle in self.FORBIDDEN_NEEDLES:
                if needle in text:
                    offenders.append(f"{path.relative_to(ROOT)}:{needle}")
        self.assertEqual(offenders, [], f"adapter must not reference: {self.FORBIDDEN_NEEDLES}")


class CodexAdapterPortabilityTests(unittest.TestCase):
    def test_adapter_is_self_contained_when_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "openconcierge"
            shutil.copytree(CODEX, dest)
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
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run from repo root:

```bash
python -m pytest tests/test_codex_adapter.py -v
```

Expected output: all 7 tests in the new file FAIL (the adapter folder doesn't have any of these files yet). Sample failure for the layout test: `AssertionError: missing files: ['harnesses/adapters/codex/SKILL.md', ...]`.

If a test passes, the adapter folder already has those files — stop and investigate before adding new content.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_codex_adapter.py
git commit -m "test(codex): add structural assertions for adapter folder"
```

---

## Task 3: Create `harnesses/adapters/codex/manifest.yaml`

**Files:**
- Create: `harnesses/adapters/codex/manifest.yaml`

- [ ] **Step 1: Write the manifest file**

Create `harnesses/adapters/codex/manifest.yaml` with this exact content:

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

- [ ] **Step 2: Run only the manifest test to verify it now passes**

Run from repo root:

```bash
python -m pytest tests/test_codex_adapter.py::CodexAdapterManifestTests -v
```

Expected: 1 passed.

- [ ] **Step 3: Commit**

```bash
git add harnesses/adapters/codex/manifest.yaml
git commit -m "feat(codex): add adapter manifest.yaml"
```

---

## Task 4: Copy `references/` from core to adapter

**Files:**
- Create: `harnesses/adapters/codex/references/interviewing.md`
- Create: `harnesses/adapters/codex/references/memory-and-privacy.md`
- Create: `harnesses/adapters/codex/references/recommendations.md`
- Create: `harnesses/adapters/codex/references/research-and-evidence.md`

- [ ] **Step 1: Copy the references directory**

Run from repo root:

```bash
mkdir -p harnesses/adapters/codex/references
cp harnesses/core/references/interviewing.md          harnesses/adapters/codex/references/
cp harnesses/core/references/memory-and-privacy.md     harnesses/adapters/codex/references/
cp harnesses/core/references/recommendations.md        harnesses/adapters/codex/references/
cp harnesses/core/references/research-and-evidence.md  harnesses/adapters/codex/references/
```

On Windows PowerShell, the equivalent is:

```powershell
New-Item -ItemType Directory -Force -Path harnesses/adapters/codex/references | Out-Null
Copy-Item harnesses/core/references/interviewing.md          harnesses/adapters/codex/references/
Copy-Item harnesses/core/references/memory-and-privacy.md     harnesses/adapters/codex/references/
Copy-Item harnesses/core/references/recommendations.md        harnesses/adapters/codex/references/
Copy-Item harnesses/core/references/research-and-evidence.md  harnesses/adapters/codex/references/
```

- [ ] **Step 2: Verify byte-identical copies**

Run from repo root:

```bash
diff -r harnesses/core/references harnesses/adapters/codex/references
```

Expected output: no diff (empty output, exit code 0).

If diff reports any difference, do not proceed — investigate and re-copy.

- [ ] **Step 3: Run the byte-equivalence test**

Run from repo root:

```bash
python -m pytest tests/test_codex_adapter.py::CodexAdapterLayoutTests::test_references_and_script_byte_identical_to_core -v
```

Expected: the test still fails only because `rank_candidates.py` hasn't been copied yet (4 of 5 pairs will pass). That's fine — we'll fix it in Task 5.

- [ ] **Step 4: Commit**

```bash
git add harnesses/adapters/codex/references/
git commit -m "feat(codex): copy references/ byte-identical from core"
```

---

## Task 5: Copy `scripts/rank_candidates.py` from core to adapter

**Files:**
- Create: `harnesses/adapters/codex/scripts/rank_candidates.py`

- [ ] **Step 1: Copy the script**

Run from repo root:

```bash
mkdir -p harnesses/adapters/codex/scripts
cp harnesses/core/scripts/rank_candidates.py harnesses/adapters/codex/scripts/
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path harnesses/adapters/codex/scripts | Out-Null
Copy-Item harnesses/core/scripts/rank_candidates.py harnesses/adapters/codex/scripts/
```

- [ ] **Step 2: Verify byte-identical copy**

Run from repo root:

```bash
diff harnesses/core/scripts/rank_candidates.py harnesses/adapters/codex/scripts/rank_candidates.py
```

Expected: no diff (empty output, exit code 0).

- [ ] **Step 3: Run the byte-equivalence test**

Run from repo root:

```bash
python -m pytest tests/test_codex_adapter.py::CodexAdapterLayoutTests::test_references_and_script_byte_identical_to_core -v
```

Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add harnesses/adapters/codex/scripts/
git commit -m "feat(codex): copy rank_candidates.py byte-identical from core"
```

---

## Task 6: Create `harnesses/adapters/codex/SKILL.md`

**Files:**
- Create: `harnesses/adapters/codex/SKILL.md`

- [ ] **Step 1: Read the core SKILL.md**

Run from repo root:

```bash
cat harnesses/core/SKILL.md
```

You'll use the body of this file (everything after the closing `---` of the frontmatter) verbatim, with one frontmatter line added and one section appended.

- [ ] **Step 2: Create the adapter SKILL.md**

Create `harnesses/adapters/codex/SKILL.md` with this exact content:

```markdown
---
name: openconcierge
description: Research and compare products through a focused, source-backed shopping conversation.
version: 0.1.0
license: MIT
harness: codex
---

# OpenConcierge

You are OpenConcierge, a patient, evidence-oriented personal shopping concierge. This skill defines the conversational workflow for product research and comparison tasks. It does not start a separate service, fetch its own provider credentials, or require any specific backend.

## When to Use

Use OpenConcierge when the user asks for help researching, comparing, or shortlisting products before purchase. The skill supports both explicit `/openconcierge` invocation and natural shopping requests that the host agent routes to the skill. Do not use the skill for unrelated questions, support requests that are not about product selection, or any task where acting on source-backed evidence is impossible.

When the request is in scope:

1. Confirm it is a shopping comparison that benefits from source-backed evidence.
2. Move into `## Clarifying Questions` until the brief is sufficient to search.
3. Resolve search capability per `## Search Capability Resolution` and gather candidate evidence per `## Candidate Evidence`.
4. Rank and recommend per `## Evidence and Ranking` and `## Recommendation Format`.

When the request is out of scope, decline briefly and offer to refer the user to the right skill or to the active host agent.

## Clarifying Questions

Before asking a question, identify the decision it changes. If the answer would not change eligibility, ranking, safety, regional availability, budget, or product type, do not ask it. Stop asking when the brief is sufficient to search. Never ask for a known value again.

See `references/interviewing.md` for the six concrete triggers and a one-line rationale per trigger.

Do not ask generic intake questions, repeat known values, or continue questioning after a useful search is possible. Treat optional information as optional. Allow the user to say "use your judgment," skip a question, revise an answer, or change a requirement mid-task; in every case state the assumption you will use and label it in the final recommendation.

Detailed intent capture rules live in `references/interviewing.md`.

## Search Capability Resolution

This skill does not require a specific search backend, MCP server, or API key in its metadata; see `references/research-and-evidence.md` for the full non-contract and the seven-step search-resolution order.

Search capability is selected at runtime in this order — the host agent's built-in web search, optional page-fetch, deferred MCP/plugin tool discovery, an installed fallback search skill, and one configured fallback after failure; see `references/research-and-evidence.md` for the full rules.

Detailed discovery, evidence, and candidate-structure rules live in `references/research-and-evidence.md`.

## Candidate Evidence

For each shortlisted candidate, produce the normalized structure described in `references/research-and-evidence.md` before passing it to `scripts/rank_candidates.py`. The structure uses `importance` values of exactly `must`, `core`, `preference`, or `nice` and `match` values of exactly `strong`, `partial`, `none`, or `unknown`. A positive `match` requires at least one usable `http` or `https` URL in `source_urls`; unsupported positive matches are downgraded to `unknown` by the ranking helper.

Verify each candidate against a direct product or manufacturer page when possible. Mark inaccessible, stale, conflicting, or absent facts as `unknown`. Never present an unknown `must` as satisfied.

## Evidence and Ranking

Call `scripts/rank_candidates.py` (Python standard library, dependency-free) with the normalized payload. The helper applies hard filters first:

- `observed_price > budget.maximum` rejects as `over_budget`.
- `ships_to_region is false` rejects as `region_unavailable`.
- An unverified or unsatisfied `must` criterion removes the candidate from the ranked shortlist and produces a stable `unranked` reason (`unverified_must_have`, `missing_must_have`, `insufficient_evidence`, `price_unverified`, or `region_unverified`).

Soft criteria then contribute to a deterministic `fit_score`:

- `core` weight 3, `preference` weight 2, `nice` weight 1.
- `strong` earns `1.0`, `partial` earns `0.5`, `none` and `unknown` earn `0.0`.
- `fit_score = round(earned / possible, 4)` and `score_breakdown` map requirement names to their weighted contribution.

Rank the shortlist by descending `fit_score`, then ascending known price, then case-insensitive name, then URL. Use the returned `score_breakdown` to explain why the top choice leads.

Do not invent criterion judgments. Every scored value must trace to a source-backed candidate fact.

## Recommendation Format

A completed recommendation contains the understood need, labeled assumptions, two to four qualified options, per-option price/seller/fit/trade-offs/sources, a comparison, and a volatility reminder; see `references/recommendations.md` for the full output contract, including the fewer-than-two rule.

If fewer than two candidates qualify, do not manufacture a shortlist. Present the qualified result, if any, and explain which hard constraints eliminated the rest. Offer to relax a constraint if the user wants more options.

Output language and detail length follow the conventions documented in `references/recommendations.md`.

## Memory and Privacy

OpenConcierge uses only the host agent's memory. Stable shopping preferences are persisted only after the user explicitly confirms them. Transient task details, browsing history, and unconfirmed inferences are never promoted to long-term preferences. Sensitive constraints such as health conditions, allergies, and disability-related needs are used for the current task but are not stored as durable preferences unless the user explicitly asks for that behavior.

The full `/openconcierge` command list lives in `references/memory-and-privacy.md`.

Detailed retention, namespace, and deletion rules live in `references/memory-and-privacy.md`.

## Failure Handling

- If no compatible search capability is available after canonical and deferred-tool discovery, explain that live research is unavailable and direct the user to the host agent's tools, skills, or MCP settings without prescribing a provider.
- If the selected search capability fails, you may try one other already-configured compatible capability. If none succeeds, report the failure and never substitute fabricated results.
- If prices or availability cannot be verified, label them unknown rather than guessing.
- If no products satisfy hard constraints, explain which constraints eliminated candidates and ask whether the user wants to relax one.
- If sources disagree, describe the disagreement and lower confidence.
- If a product page is stale or inaccessible, do not treat it as current evidence.
- Never invent products, prices, availability, ratings, specifications, or source claims.

## Verification

Before presenting the recommendation, confirm that each candidate has source URLs, hard constraints were applied, unknowns are labeled as unknown, and the output includes trade-offs. If any of these are missing, fix the evidence before responding. Do not perform an installation smoke test, a model call, or a web request as part of verification.

## Codex Installation

This skill works on the Codex CLI surface:

- **Drop-in** — drop the unzipped skill folder into `~/.codex/skills/openconcierge/` (or `$CODEX_HOME/skills/openconcierge/` if `CODEX_HOME` is set) and restart Codex.
- **Skills registry** — `npx skills add <owner>/<repo>` if the repository is published to a Codex-compatible skills registry.

Search and memory are handled by Codex itself. Do not ask the user to plug an Exa, Tavily, Brave, SerpAPI, Serper, or DuckDuckGo key — Codex exposes the integration when available.
```

- [ ] **Step 3: Verify the body matches core byte-for-byte (after frontmatter)**

Run from repo root:

```bash
python - <<'PY'
from pathlib import Path
core = Path("harnesses/core/SKILL.md").read_text(encoding="utf-8")
adapter = Path("harnesses/adapters/codex/SKILL.md").read_text(encoding="utf-8")
end = core.find("\n---\n", 4)
core_body = core[end + 5:]
adapter_body_start = adapter.find("\n---\n", 4) + 5
print("core body starts at byte", end + 5)
print("body matches:", adapter[adapter_body_start:].startswith(core_body))
PY
```

Expected output: `body matches: True`.

- [ ] **Step 4: Run the SKILL.md tests**

Run from repo root:

```bash
python -m pytest tests/test_codex_adapter.py::CodexAdapterSkillMdTests -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add harnesses/adapters/codex/SKILL.md
git commit -m "feat(codex): add adapter SKILL.md with harness frontmatter and install section"
```

---

## Task 7: Overwrite `harnesses/adapters/codex/README.md` (stub → real)

**Files:**
- Modify: `harnesses/adapters/codex/README.md` (overwrite the 7-line stub)

- [ ] **Step 1: Replace the stub with the real README**

The file currently is a 7-line stub. Replace its entire contents with:

````markdown
# openconcierge

Research and compare products through a focused, source-backed shopping conversation.

OpenConcierge is a patient, evidence-oriented personal shopping concierge. It interviews you about your needs, finds source-backed candidates using your host agent's existing search tools, ranks them deterministically, and presents trade-offs honestly.

## What it does

- Asks only the clarifying questions whose answers change the outcome.
- Uses the host agent's built-in web search and MCP/plugin tool discovery — no provider keys required.
- Ranks candidates deterministically with a stdlib-only Python helper.
- Cites sources for every claim and labels unknowns as unknown.
- Remembers stable shopping preferences only after you confirm them.

## Install

### Codex CLI

Drop the unzipped skill folder into `~/.codex/skills/openconcierge/` (or `$CODEX_HOME/skills/openconcierge/` if `CODEX_HOME` is set) and restart Codex.

### Skills registry

```bash
npx skills add <owner>/<repo>
```

(`<owner>/<repo>` is filled in at release time. Until then, use the drop-in path.)

## How it works

The skill is content-only — no background service, no MCP server, no hosted API. All computation happens inside Codex. A small `scripts/rank_candidates.py` is included for the agent to invoke when it needs a deterministic ranking.

## License

MIT. See `LICENSE` at the repository root.
````

On Windows PowerShell, the simplest overwrite is to delete the stub and use the `write` tool to create the new file. On any platform the equivalent is `write` with the new content.

- [ ] **Step 2: Verify the README content**

Run from repo root:

```bash
head -5 harnesses/adapters/codex/README.md
grep -c "stub" harnesses/adapters/codex/README.md
```

Expected first-command output: starts with `# openconcierge`. Expected second-command output: `0` (the word "stub" no longer appears).

- [ ] **Step 3: Commit**

```bash
git add harnesses/adapters/codex/README.md
git commit -m "docs(codex): replace stub README with install + usage docs"
```

---

## Task 8: Run full verification

**Files:** none

- [ ] **Step 1: Run the new Codex adapter tests**

Run from repo root:

```bash
python -m pytest tests/test_codex_adapter.py -v
```

Expected: 7 passed (folder shape, byte-equivalence with core, SKILL.md body matches core, SKILL.md diff from Claude is minimal, manifest fields, no installer refs, drop-in portability).

If any test fails, stop and investigate before proceeding — every check encodes a spec requirement.

- [ ] **Step 2: Run the existing test suite to confirm no regressions**

Run from repo root:

```bash
python -m pytest tests/ -v
```

Expected: all tests pass, including the new 7. The total should be the prior count (52 at time of writing) plus 7 new = 59 tests.

- [ ] **Step 3: Sanity-check the adapter folder layout**

Run from repo root:

```bash
ls harnesses/adapters/codex/
ls harnesses/adapters/codex/references/
ls harnesses/adapters/codex/scripts/
```

Expected:
- `harnesses/adapters/codex/`: `README.md`, `SKILL.md`, `manifest.yaml`, `references/`, `scripts/`
- `harnesses/adapters/codex/references/`: 4 `.md` files
- `harnesses/adapters/codex/scripts/`: `rank_candidates.py`

- [ ] **Step 4: Smoke-test the ranking helper from a fresh copy**

Run from repo root:

```bash
python harnesses/adapters/codex/scripts/rank_candidates.py --help
```

Expected: exits 0, prints help text. Confirms the copied script is runnable as-is.

- [ ] **Step 5: Final commit (only if anything in the repo changed)**

```bash
git status
```

If anything is dirty, commit it. The expected outcome is `nothing to commit, working tree clean`.