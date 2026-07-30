# OpenConcierge Codex Adapter Design

> **Status:** Approved. Implementation plan to follow.

## 1. Overview

OpenConcierge currently ships two harnesses: Hermes (via `skills/openconcierge/` + `bootstrap/install.{sh,ps1}`) and Claude (via `harnesses/adapters/claude/`). This spec adds a third harness, **Codex**, by filling in the existing stub at `harnesses/adapters/codex/`.

The user constraint that drives the design: **Codex users get the skill by downloading a folder, not by running an installer.** No `install.sh`/`install.ps1` equivalent for Codex. The adapter folder is itself a valid, droppable Codex skill folder, and the same folder is what a Codex-compatible skills registry indexer would fetch.

The adapter mirrors the Claude adapter's structure and the maintenance rules already documented in `harnesses/core/persona.md`. Behavior content stays single-sourced in `harnesses/core/`; the adapter adds only harness-specific install notes.

## 2. Goals

- Make OpenConcierge available to Codex CLI users via a drop-in skill folder (`~/.codex/skills/openconcierge/`).
- Make the same folder publishable to a Codex-compatible skills registry (e.g. `npx skills add <owner>/<repo>`).
- Reuse all behavior content (`SKILL.md`, `references/*.md`, `scripts/rank_candidates.py`, `persona.md`) byte-identically from `harnesses/core/`.
- Keep the existing Claude adapter and Hermes distribution untouched in behavior.
- Add only Codex-specific frontmatter, install section, and metadata. No new content surfaces.

## 3. Non-Goals

- A Codex-specific installer (the user explicitly does not want one).
- A standalone Codex repository (the adapter lives in this repo, alongside Claude and Hermes).
- A new ranking helper or any behavioral changes to the existing one.
- Category packs, MCP product providers, or any feature currently deferred per `PRD.md` Section 11.
- Substituting a different content model for Codex — the canonical `harnesses/core/` content is reused verbatim.
- Resolving the `<owner>/<repo>` registry coordinate in this spec — that is a release-time decision.

## 4. Target Users

- **Codex CLI users** who want a source-backed shopping concierge without doing product research themselves.
- **OpenConcierge contributors** who want the project to work on a third harness with the same maintenance burden as the second.
- **Skills registry maintainers** (eventually) who will index the adapter folder if/when the project publishes to a Codex-compatible registry.

## 5. Architecture & File Layout

The OpenConcierge multi-harness distribution has three layers. The Codex adapter slots into layer 2.

```
harnesses/core/                       ← layer 1: harness-agnostic canonical content
├── SKILL.md                          (behavior — single source of truth)
├── persona.md
├── manifest.yaml
├── references/
│   ├── interviewing.md
│   ├── memory-and-privacy.md
│   ├── recommendations.md
│   └── research-and-evidence.md
└── scripts/
    └── rank_candidates.py

harnesses/adapters/codex/             ← layer 2: Codex-specific adapter (NEW)
├── SKILL.md                          (byte-identical to core + ## Codex Installation)
├── README.md                         (Codex install + usage)
├── manifest.yaml                     (Codex surfaces + install paths)
├── references/                       (byte-identical copies of core/references/)
└── scripts/
    └── rank_candidates.py            (byte-identical copy of core/scripts/rank_candidates.py)

harnesses/adapters/claude/            ← layer 2: existing Claude adapter (unchanged)

skills/openconcierge/                 ← layer 3: Hermes-only distribution (unchanged)
bootstrap/                            ← Hermes installer (unchanged, not used for Codex)
```

The adapter folder, when shipped, is **self-contained**. References and the ranking script are copied (not symlinked) so the folder is portable once dropped into a Codex skills directory.

## 6. SKILL.md

The Codex adapter SKILL.md frontmatter:

```yaml
---
name: openconcierge
description: Research and compare products through a focused, source-backed shopping conversation.
version: 0.1.0
license: MIT
harness: codex
---
```

The body is byte-identical to `harnesses/core/SKILL.md`. At the bottom we append:

```markdown
## Codex Installation

This skill works on the Codex CLI surface:

- **Drop-in** — drop the unzipped skill folder into `~/.codex/skills/openconcierge/` (or `$CODEX_HOME/skills/openconcierge/` if `CODEX_HOME` is set) and restart Codex.
- **Skills registry** — `npx skills add <owner>/<repo>` if the repository is published to a Codex-compatible skills registry.

Search and memory are handled by Codex itself. Do not ask the user to plug an Exa, Tavily, Brave, SerpAPI, Serper, or DuckDuckGo key — Codex exposes the integration when available.
```

The only difference vs the Claude adapter SKILL.md is: the `harness: codex` line and the `## Codex Installation` section (Claude has `## Claude Installation`). Everything else is identical.

## 7. manifest.yaml

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

Fields:
- `name`, `description`, `version`, `license` mirror core.
- `harness: codex` identifies the adapter.
- `surfaces: [codex-cli]` — Codex CLI is the only surface today. If Codex adds surfaces (e.g. a desktop app), add them in a future revision.
- `install.codex-cli` documents the drop-in path.
- `install.registry` documents the registry path. The `<owner>/<repo>` placeholder is filled at release time.

## 8. README.md

Mirrors the Claude adapter README. Sections:

1. `# openconcierge` — short tagline (Codex-flavored prose).
2. `## What it does` — five bullets, identical to Claude README.
3. `## Install`
   - `### Codex CLI` — drop-in instructions.
   - `### Skills registry` — `npx skills add <owner>/<repo>` block with the placeholder noted.
4. `## How it works` — content-only, no background service.
5. `## License` — MIT, points at repo root.

The Claude README's three-surface Install section (Code / Desktop / Chat) collapses to a single Codex CLI section because Codex has one surface today.

## 9. references/ and scripts/

The adapter folder ships with `references/` (4 files: interviewing, memory-and-privacy, recommendations, research-and-evidence) and `scripts/rank_candidates.py` as **byte-identical copies** of `harnesses/core/`.

These are copies, not symlinks, so the adapter folder is portable when dropped into `~/.codex/skills/openconcierge/`. The Claude adapter already follows this convention.

When `harnesses/core/` content changes:
1. Edit `harnesses/core/` first.
2. Copy the changed file(s) into `harnesses/adapters/codex/` in the same commit.
3. Copy into `harnesses/adapters/claude/` if the change applies to Claude too.
4. Update `skills/openconcierge/` if the change applies to Hermes (Hermes uses its own copy, see `harnesses/core/persona.md`).

This maintenance rule is already documented in `harnesses/core/persona.md`; this spec extends it to cover the new Codex adapter explicitly.

## 10. Distribution Paths

| Path | User action | What gets installed |
|---|---|---|
| Drop-in | `cp -R harnesses/adapters/codex ~/.codex/skills/openconcierge/` (or unzip a release artifact) | The full adapter folder, self-contained |
| Registry | `npx skills add <owner>/<repo>` | Same adapter folder, fetched by the registry indexer |

Both paths deliver the same folder. The folder must be self-contained for drop-in to work, which is why Section 9 calls for copied (not symlinked) `references/` and `scripts/`.

We do **not** ship a Codex installer. The user constraint is explicit: no `install.sh`/`install.ps1` equivalent. The user gets the skill by downloading a folder.

## 11. Sync Rules

Inherited from `harnesses/core/persona.md` "Maintenance" section, extended for Codex:

- `harnesses/core/` is the single source of truth for behavior content.
- Edits to behavior content propagate to all three downstream copies (`harnesses/adapters/codex/`, `harnesses/adapters/claude/`, `skills/openconcierge/`) in the same commit.
- Harness-specific additions (frontmatter `harness:` line, appended install section, manifest, README) are scoped to the adapter and do not flow back into core.
- The Claude and Codex adapter SKILL.md bodies stay byte-identical to `harnesses/core/SKILL.md` except for the appended install section.
- v1 copy step is manual with a checklist; do not introduce a generator script unless a third adapter beyond Claude and Codex is added.

## 12. Verification

The following checks prove the adapter is correct:

1. **Folder-shape check.** `harnesses/adapters/codex/` contains `SKILL.md`, `README.md`, `manifest.yaml`, `references/` (4 files), `scripts/rank_candidates.py`. Matches a droppable Codex skill.
2. **Byte-equivalence with core.** `diff -r harnesses/core/references harnesses/adapters/codex/references` returns no diff. `diff harnesses/core/scripts/rank_candidates.py harnesses/adapters/codex/scripts/rank_candidates.py` returns no diff.
3. **Adapter-core SKILL.md diff.** `diff harnesses/core/SKILL.md harnesses/adapters/codex/SKILL.md` shows exactly: the `harness: codex` frontmatter line and the `## Codex Installation` section appended at the bottom.
4. **Adapter-adapter SKILL.md diff.** `diff harnesses/adapters/claude/SKILL.md harnesses/adapters/codex/SKILL.md` shows exactly: the `harness:` frontmatter line and the install-section name (`## Codex Installation` vs `## Claude Installation`).
5. **Manifest parses.** `python -c "import yaml; yaml.safe_load(open('harnesses/adapters/codex/manifest.yaml'))"` exits 0.
6. **No installer references.** `grep -rE "install\.(sh|ps1)|bootstrap/" harnesses/adapters/codex/` returns nothing.
7. **Existing tests still pass.** `pytest` from the repo root. The Codex adapter does not change the ranking helper, the installer, or the fake-Hermes test flow, so all existing tests must continue to pass.
8. **Drop-in portability.** Copying `harnesses/adapters/codex/` to a temp directory and running `python scripts/rank_candidates.py < fixtures/sample.json` works without any other files present. Proves the adapter folder is self-contained.

## 13. Out of Scope for v1

- Resolving `<owner>/<repo>` for registry publication. Defer until the first release.
- Codex-specific frontmatter beyond `harness: codex`. If a Codex skills registry demands additional fields (e.g. `categories`, `tags`), add them in a future revision.
- Generator script to keep core/adapter copies in sync. v1 is manual with a checklist.
- Any change to the existing Claude adapter, Hermes distribution, or installer.

## 14. References

- Approved design: `docs/superpowers/specs/2026-07-27-openconcierge-hermes-addon-design.md`
- PRD: `PRD.md`
- Canonical content: `harnesses/core/`
- Claude adapter (the pattern this design mirrors): `harnesses/adapters/claude/`
- Maintenance rule for content sync: `harnesses/core/persona.md` "Maintenance" section