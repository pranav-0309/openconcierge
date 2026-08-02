# OpenConcierge OpenClaw Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill in the existing `harnesses/adapters/openclaw/` stub so OpenConcierge is available to OpenClaw users via the native `openclaw skills install` CLI (ClawHub, Git, and local-directory sources) and as a droppable skill folder for the shared-managed or per-workspace install scopes.

**Architecture:** Mirror the existing `harnesses/adapters/codex/` pattern. Behavior content (`SKILL.md` body, `references/*.md`, `scripts/rank_candidates.py`) is byte-identical with `harnesses/core/`. The adapter adds three OpenClaw-specific files (`SKILL.md` with `harness: openclaw` and an appended install section, `manifest.yaml`, `README.md`) plus a byte-identical `references/` and `scripts/` folder so the drop-in folder is self-contained. A small Python one-liner constructs the adapter SKILL.md from core so the plan doesn't have to inline 95 lines of body.

**Tech Stack:** Python 3.12 (stdlib only — no third-party deps added), Pytest + `unittest.TestCase` (existing project convention), PowerShell on Windows / Bash on macOS/Linux for copy operations.

---

## File Structure

### Files to create

| Path | Responsibility |
|---|---|
| `harnesses/adapters/openclaw/SKILL.md` | Byte-identical body to `harnesses/core/SKILL.md` + `harness: openclaw` frontmatter line + appended `## OpenClaw Installation` section |
| `harnesses/adapters/openclaw/README.md` | User-facing install + usage docs (overwrites existing 7-line stub) |
| `harnesses/adapters/openclaw/manifest.yaml` | Declares `surfaces: [openclaw-workspace, openclaw-global]`, the four install paths (workspace, global, drop-in, git) |
| `harnesses/adapters/openclaw/references/interviewing.md` | Byte-identical copy of `harnesses/core/references/interviewing.md` |
| `harnesses/adapters/openclaw/references/memory-and-privacy.md` | Byte-identical copy of `harnesses/core/references/memory-and-privacy.md` |
| `harnesses/adapters/openclaw/references/recommendations.md` | Byte-identical copy of `harnesses/core/references/recommendations.md` |
| `harnesses/adapters/openclaw/references/research-and-evidence.md` | Byte-identical copy of `harnesses/core/references/research-and-evidence.md` |
| `harnesses/adapters/openclaw/scripts/rank_candidates.py` | Byte-identical copy of `harnesses/core/scripts/rank_candidates.py` |
| `tests/test_openclaw_adapter.py` | Structural assertions: folder shape, byte-equivalence, manifest parses, no installer references, drop-in portability |

### Files to modify

| Path | Change |
|---|---|
| `harnesses/adapters/openclaw/README.md` | Overwrite the existing 7-line stub README with the real README |

### Files explicitly NOT touched

- `harnesses/core/` — canonical content stays single-sourced
- `harnesses/adapters/codex/` and `harnesses/adapters/claude/` — sibling adapters unchanged
- `skills/openconcierge/` — Hermes distribution is unchanged
- `bootstrap/` — Hermes installer is unchanged; OpenClaw has no installer per spec
- `.claude-plugin/marketplace.json` — skills.sh targeting; not relevant to OpenClaw
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

- [ ] **Step 2: Verify the existing OpenClaw stub**

Run from repo root:

```bash
ls harnesses/adapters/openclaw/
```

Expected output: a single `README.md` (the stub). The folder currently contains nothing else.

- [ ] **Step 3: Verify pytest discovers existing tests**

Run from repo root:

```bash
python -m pytest tests/ --collect-only
```

Expected output: 59 collected tests (52 prior + 7 from `test_codex_adapter.py`). The exact number matters less than that pytest works and tests collect.

If pytest errors, fix the environment before proceeding.

- [ ] **Step 4: Commit baseline check (no changes yet)**

```bash
git status
```

Expected: clean tree or only the spec doc we just committed. If anything else is dirty, commit or stash before proceeding.

- [ ] **Step 5: Optional — work in a dedicated worktree**

If you want isolation from the main working tree, create a worktree first:

```bash
git worktree add ../openconcierge-openclaw -b feat/openclaw-adapter
```

Then `cd ../openconcierge-openclaw` and run all subsequent commands from there. Skip this step if you're happy working in the main checkout.

---

## Task 2: Write failing tests for OpenClaw adapter structure

**Files:**
- Create: `tests/test_openclaw_adapter.py`

- [ ] **Step 1: Create the test file with all five structural tests**

Create `tests/test_openclaw_adapter.py` with this exact content:

```python
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
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run from repo root:

```bash
python -m pytest tests/test_openclaw_adapter.py -v
```

Expected output: all 7 tests in the new file FAIL (the adapter folder doesn't have any of these files yet). Sample failure for the layout test: `AssertionError: missing files: ['harnesses/adapters/openclaw/SKILL.md', ...]`.

If a test passes, the adapter folder already has those files — stop and investigate before adding new content.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_openclaw_adapter.py
git commit -m "test(openclaw): add structural assertions for adapter folder"
```

---

## Task 3: Create `harnesses/adapters/openclaw/manifest.yaml`

**Files:**
- Create: `harnesses/adapters/openclaw/manifest.yaml`

- [ ] **Step 1: Write the manifest file**

Create `harnesses/adapters/openclaw/manifest.yaml` with this exact content:

```yaml
name: openconcierge
description: Research and compare products through a focused, source-backed shopping conversation.
version: 0.1.0
license: MIT
harness: openclaw
surfaces:
  - openclaw-workspace
  - openclaw-global
install:
  openclaw-workspace: "openclaw skills install @<owner>/openconcierge"
  openclaw-global: "openclaw skills install @<owner>/openconcierge --global"
  drop-in: "copy the skill folder into ~/.openclaw/skills/openconcierge/ (or $OPENCLAW_STATE_DIR/skills/openconcierge/)"
  git: "openclaw skills install git:<owner>/<repo>@<ref>"
```

- [ ] **Step 2: Run only the manifest test to verify it now passes**

Run from repo root:

```bash
python -m pytest tests/test_openclaw_adapter.py::OpenClawAdapterManifestTests -v
```

Expected: 1 passed.

- [ ] **Step 3: Commit**

```bash
git add harnesses/adapters/openclaw/manifest.yaml
git commit -m "feat(openclaw): add adapter manifest.yaml"
```

---

## Task 4: Copy `references/` from core to adapter

**Files:**
- Create: `harnesses/adapters/openclaw/references/interviewing.md`
- Create: `harnesses/adapters/openclaw/references/memory-and-privacy.md`
- Create: `harnesses/adapters/openclaw/references/recommendations.md`
- Create: `harnesses/adapters/openclaw/references/research-and-evidence.md`

- [ ] **Step 1: Copy the references directory**

On macOS/Linux, run from repo root:

```bash
mkdir -p harnesses/adapters/openclaw/references
cp harnesses/core/references/interviewing.md          harnesses/adapters/openclaw/references/
cp harnesses/core/references/memory-and-privacy.md     harnesses/adapters/openclaw/references/
cp harnesses/core/references/recommendations.md        harnesses/adapters/openclaw/references/
cp harnesses/core/references/research-and-evidence.md  harnesses/adapters/openclaw/references/
```

On Windows PowerShell, run from repo root:

```powershell
New-Item -ItemType Directory -Force -Path harnesses/adapters/openclaw/references | Out-Null
Copy-Item harnesses/core/references/interviewing.md          harnesses/adapters/openclaw/references/
Copy-Item harnesses/core/references/memory-and-privacy.md     harnesses/adapters/openclaw/references/
Copy-Item harnesses/core/references/recommendations.md        harnesses/adapters/openclaw/references/
Copy-Item harnesses/core/references/research-and-evidence.md  harnesses/adapters/openclaw/references/
```

- [ ] **Step 2: Verify byte-identical copies**

On macOS/Linux, run from repo root:

```bash
diff -r harnesses/core/references harnesses/adapters/openclaw/references
```

On Windows PowerShell, run all four comparisons in one go:

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

Expected (macOS/Linux): no diff (empty output, exit code 0). Expected (PowerShell): `OK: all four reference files are byte-identical`.

If any difference is reported, do not proceed — investigate and re-copy.

- [ ] **Step 3: Run the byte-equivalence test for references**

Run from repo root:

```bash
python -m pytest "tests/test_openclaw_adapter.py::OpenClawAdapterLayoutTests::test_references_and_script_byte_identical_to_core" -v
```

Expected: the test still fails only because `rank_candidates.py` hasn't been copied yet (4 of 5 pairs will pass). That's fine — we'll fix it in Task 5.

- [ ] **Step 4: Commit**

```bash
git add harnesses/adapters/openclaw/references/
git commit -m "feat(openclaw): copy references/ byte-identical from core"
```

---

## Task 5: Copy `scripts/rank_candidates.py` from core to adapter

**Files:**
- Create: `harnesses/adapters/openclaw/scripts/rank_candidates.py`

- [ ] **Step 1: Copy the script**

On macOS/Linux, run from repo root:

```bash
mkdir -p harnesses/adapters/openclaw/scripts
cp harnesses/core/scripts/rank_candidates.py harnesses/adapters/openclaw/scripts/
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path harnesses/adapters/openclaw/scripts | Out-Null
Copy-Item harnesses/core/scripts/rank_candidates.py harnesses/adapters/openclaw/scripts/
```

- [ ] **Step 2: Verify byte-identical copy**

On macOS/Linux, run from repo root:

```bash
diff harnesses/core/scripts/rank_candidates.py harnesses/adapters/openclaw/scripts/rank_candidates.py
```

On Windows PowerShell:

```powershell
fc /b harnesses/core/scripts/rank_candidates.py harnesses/adapters/openclaw/scripts/rank_candidates.py
```

Expected (macOS/Linux): no diff (empty output, exit code 0). Expected (PowerShell): "FC: no differences encountered".

If any difference is reported, do not proceed — investigate and re-copy.

- [ ] **Step 3: Run the byte-equivalence test for references + script**

Run from repo root:

```bash
python -m pytest "tests/test_openclaw_adapter.py::OpenClawAdapterLayoutTests::test_references_and_script_byte_identical_to_core" -v
```

Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add harnesses/adapters/openclaw/scripts/
git commit -m "feat(openclaw): copy rank_candidates.py byte-identical from core"
```

---

## Task 6: Create `harnesses/adapters/openclaw/SKILL.md`

**Files:**
- Create: `harnesses/adapters/openclaw/SKILL.md`

- [ ] **Step 1: Construct the adapter SKILL.md from core**

We construct the adapter SKILL.md by combining the OpenClaw-specific frontmatter, the body of `harnesses/core/SKILL.md`, and the OpenClaw install section. Use a Python one-liner so the body is read live from core (no inlined 95-line body to drift).

Run from repo root:

```bash
python - <<'PY'
from pathlib import Path
import re

core_text = Path("harnesses/core/SKILL.md").read_text(encoding="utf-8")
m = re.match(r"^---\n.*?\n---\n", core_text, re.DOTALL)
if not m:
    raise SystemExit("core SKILL.md has no YAML frontmatter")
core_body = core_text[m.end():]

frontmatter = (
    "---\n"
    "name: openconcierge\n"
    "description: Research and compare products through a focused, source-backed shopping conversation.\n"
    "version: 0.1.0\n"
    "license: MIT\n"
    "harness: openclaw\n"
    "---\n"
)

install_section = (
    "\n## OpenClaw Installation\n"
    "\n"
    "This skill works on OpenClaw (CLI surface, two install scopes):\n"
    "\n"
    "- **Workspace (default)** - `openclaw skills install @<owner>/openconcierge` installs into the active workspace's `skills/` directory, visible to that workspace's agent.\n"
    "- **Shared managed (`--global`)** - `openclaw skills install @<owner>/openconcierge --global` installs into `~/.openclaw/skills/openconcierge/`, visible to all local agents on the machine.\n"
    "- **Drop-in** - copy the unzipped skill folder into `~/.openclaw/skills/openconcierge/` (or `<workspace>/skills/openconcierge/`) and restart OpenClaw. Honors `OPENCLAW_STATE_DIR` if set.\n"
    "- **Git install** - `openclaw skills install git:<owner>/<repo>@<ref>` for users who want a specific revision.\n"
    "\n"
    "`<owner>/<repo>` and the ClawHub slug are filled at release time. Search and memory are handled by OpenClaw itself. Do not ask the user to plug an Exa, Tavily, Brave, SerpAPI, Serper, or DuckDuckGo key - OpenClaw exposes the integration when available.\n"
)

Path("harnesses/adapters/openclaw/SKILL.md").write_text(frontmatter + core_body + install_section, encoding="utf-8")
print("wrote harnesses/adapters/openclaw/SKILL.md")
PY
```

On Windows PowerShell, the equivalent is to save the same script to a temp file and run it with `python`. Save the block above (between the `PY` markers, without the markers) to a file like `build_skill_md.py`, then run:

```powershell
python build_skill_md.py
Remove-Item build_skill_md.py
```

Either way, expected output: `wrote harnesses/adapters/openclaw/SKILL.md`.

- [ ] **Step 2: Verify the body matches core byte-for-byte (after frontmatter)**

Run from repo root:

```bash
python - <<'PY'
from pathlib import Path
import re

core = Path("harnesses/core/SKILL.md").read_text(encoding="utf-8")
adapter = Path("harnesses/adapters/openclaw/SKILL.md").read_text(encoding="utf-8")

core_m = re.match(r"^---\n.*?\n---\n", core, re.DOTALL)
core_body = core[core_m.end():]

adapter_m = re.match(r"^---\n.*?\n---\n", adapter, re.DOTALL)
adapter_body_after_fm = adapter[adapter_m.end():]

print("core body starts at byte", core_m.end())
print("body matches:", adapter_body_after_fm.startswith(core_body))
print("install section present:", "## OpenClaw Installation" in adapter_body_after_fm[len(core_body):])
print("frontmatter has harness: openclaw:", "harness: openclaw" in adapter[:adapter_m.end()])
PY
```

Expected output: `body matches: True`, `install section present: True`, `frontmatter has harness: openclaw: True`.

If any line is `False`, stop and investigate. The most common failure is the `^---\n.*?\n---\n` regex not matching the frontmatter — check that the core SKILL.md has a normal `---` opener and closer.

- [ ] **Step 3: Run the SKILL.md tests**

Run from repo root:

```bash
python -m pytest tests/test_openclaw_adapter.py::OpenClawAdapterSkillMdTests -v
```

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add harnesses/adapters/openclaw/SKILL.md
git commit -m "feat(openclaw): add adapter SKILL.md with harness frontmatter and install section"
```

---

## Task 7: Overwrite `harnesses/adapters/openclaw/README.md` (stub → real)

**Files:**
- Modify: `harnesses/adapters/openclaw/README.md` (overwrite the 7-line stub)

- [ ] **Step 1: Replace the stub with the real README**

The file currently is a 7-line stub. Replace its entire contents with this content:

````markdown
# openconcierge

Research and compare products through a focused, source-backed shopping conversation.

OpenConcierge is a patient, evidence-oriented personal shopping concierge. It interviews you about your needs, finds source-backed candidates using your host agent's existing search tools, ranks them deterministically, and presents trade-offs honestly.

## What it does

- Asks only the clarifying questions whose answers change the outcome.
- Uses the host agent's built-in web search and MCP/plugin tool discovery - no provider keys required.
- Ranks candidates deterministically with a stdlib-only Python helper.
- Cites sources for every claim and labels unknowns as unknown.
- Remembers stable shopping preferences only after you confirm them.

## Install

### Workspace (default)

```bash
openclaw skills install @<owner>/openconcierge
```

Installs into the active workspace's `skills/` directory, visible to that workspace's agent.

### Shared managed (--global)

```bash
openclaw skills install @<owner>/openconcierge --global
```

Installs into `~/.openclaw/skills/openconcierge/`, visible to all local agents on the machine.

### Drop-in

Drop the unzipped skill folder into `~/.openclaw/skills/openconcierge/` (or `<workspace>/skills/openconcierge/`) and restart OpenClaw. Honors `OPENCLAW_STATE_DIR` if set.

### Git install

```bash
openclaw skills install git:<owner>/<repo>@<ref>
```

`@<owner>/<repo>` and the ClawHub slug are filled in at release time. Until then, use the drop-in or Git install.

## How it works

The skill is content-only - no background service, no MCP server, no hosted API. All computation happens inside OpenClaw. A small `scripts/rank_candidates.py` is included for the agent to invoke when it needs a deterministic ranking.

## License

MIT. See `LICENSE` at the repository root.
````

On any platform, the simplest overwrite is to delete the stub and use the `write` tool to create the new file with the content above. Alternatively, run the shell command:

On macOS/Linux:

```bash
cat > harnesses/adapters/openclaw/README.md <<'EOF'
[paste the content above between the markers]
EOF
```

On Windows PowerShell, use `Set-Content` with a here-string, or simply use the `write` tool with the full content.

- [ ] **Step 2: Verify the README content**

On macOS/Linux, run from repo root:

```bash
head -5 harnesses/adapters/openclaw/README.md
grep -c "stub" harnesses/adapters/openclaw/README.md
```

On Windows PowerShell:

```powershell
Get-Content harnesses/adapters/openclaw/README.md -TotalCount 5
(Select-String -Path harnesses/adapters/openclaw/README.md -Pattern "stub").Count
```

Expected first-command output: starts with `# openconcierge`. Expected second-command output: `0` (the word "stub" no longer appears).

- [ ] **Step 3: Run the README-adjacent tests (no-installer + portability)**

Run from repo root:

```bash
python -m pytest tests/test_openclaw_adapter.py::OpenClawAdapterNoInstallerTests tests/test_openclaw_adapter.py::OpenClawAdapterPortabilityTests -v
```

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add harnesses/adapters/openclaw/README.md
git commit -m "docs(openclaw): replace stub README with install + usage docs"
```

---

## Task 8: Run full verification

**Files:** none

- [ ] **Step 1: Run the new OpenClaw adapter tests**

Run from repo root:

```bash
python -m pytest tests/test_openclaw_adapter.py -v
```

Expected: 7 passed (folder shape, byte-equivalence with core, SKILL.md body matches core, SKILL.md diff from Codex is minimal, manifest fields, no installer refs, drop-in portability).

If any test fails, stop and investigate before proceeding - every check encodes a spec requirement.

- [ ] **Step 2: Run the existing test suite to confirm no regressions**

Run from repo root:

```bash
python -m pytest tests/ -v
```

Expected: all tests pass, including the 7 new ones. The total should be the prior count (59 at time of writing) plus 7 new = 66 tests.

- [ ] **Step 3: Sanity-check the adapter folder layout**

Run from repo root:

On macOS/Linux:

```bash
ls harnesses/adapters/openclaw/
ls harnesses/adapters/openclaw/references/
ls harnesses/adapters/openclaw/scripts/
```

On Windows PowerShell:

```powershell
Get-ChildItem harnesses/adapters/openclaw/
Get-ChildItem harnesses/adapters/openclaw/references/
Get-ChildItem harnesses/adapters/openclaw/scripts/
```

Expected:
- `harnesses/adapters/openclaw/`: `README.md`, `SKILL.md`, `manifest.yaml`, `references/`, `scripts/`
- `harnesses/adapters/openclaw/references/`: 4 `.md` files
- `harnesses/adapters/openclaw/scripts/`: `rank_candidates.py`

- [ ] **Step 4: Smoke-test the ranking helper from a fresh copy**

Run from repo root:

```bash
python harnesses/adapters/openclaw/scripts/rank_candidates.py --help
```

Expected: exits 0, prints help text. Confirms the copied script is runnable as-is.

- [ ] **Step 5: Verify the no-installer rule at the shell level**

On macOS/Linux, run from repo root:

```bash
grep -rE "install\.(sh|ps1)|bootstrap/" harnesses/adapters/openclaw/ || echo "OK: no installer references"
```

On Windows PowerShell:

```powershell
$results = Select-String -Path "harnesses/adapters/openclaw/*","harnesses/adapters/openclaw/*/*" -Pattern "install\.(sh|ps1)|bootstrap/"
if ($results) { $results | Format-List; Write-Error "forbidden installer references found" } else { Write-Output "OK: no installer references" }
```

Expected: `OK: no installer references`. (On PowerShell, the `Select-String` will error if it finds no files matching the literal — that's fine, treat it as `OK` if the script reports no matches.)

If any forbidden string is reported, fix it before completing the task.

- [ ] **Step 6: Final commit (only if anything in the repo changed)**

```bash
git status
```

If anything is dirty, commit it. The expected outcome is `nothing to commit, working tree clean`.
