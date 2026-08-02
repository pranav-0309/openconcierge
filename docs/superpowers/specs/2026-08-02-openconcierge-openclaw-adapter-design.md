# OpenConcierge OpenClaw Adapter Design

> **Status:** Approved. Implementation plan to follow.

## 1. Overview

OpenConcierge currently ships three harnesses: Hermes (via `skills/openconcierge/` + `bootstrap/install.{sh,ps1}`), Claude (via `harnesses/adapters/claude/`), and Codex (via `harnesses/adapters/codex/`). This spec adds a fourth harness, **OpenClaw**, by filling in the existing stub at `harnesses/adapters/openclaw/`.

The adapter mirrors the Codex adapter's structure and the maintenance rules already documented in `harnesses/core/persona.md`. Behavior content stays single-sourced in `harnesses/core/`; the adapter adds only OpenClaw-specific frontmatter, install notes, and a manifest that surfaces OpenClaw's two install scopes.

The OpenClaw installer convention is documented in the OpenClaw docs at `https://docs.openclaw.ai/cli/skills` and `https://docs.openclaw.ai/tools/skills`. OpenClaw exposes a single CLI surface but two install scopes (workspace vs. shared managed via `--global`), accepts ClawHub `@owner/<slug>` references, Git `git:owner/repo@ref` references, and local directory paths, and honors `OPENCLAW_STATE_DIR` as the state-directory override (defaults to `~/.openclaw`). The adapter surfaces each of these install paths.

## 2. Goals

- Make OpenConcierge available to OpenClaw users via the native `openclaw skills install` CLI for ClawHub, Git, and local-directory sources.
- Make the same folder shippable as a droppable skill folder for `~/.openclaw/skills/openconcierge/` (shared managed) or `<workspace>/skills/openconcierge/` (per-workspace), with `OPENCLAW_STATE_DIR` honored.
- Reuse all behavior content (`SKILL.md`, `references/*.md`, `scripts/rank_candidates.py`, `persona.md`) byte-identically from `harnesses/core/`.
- Keep the existing Claude and Codex adapters and the Hermes distribution untouched in behavior.
- Add only OpenClaw-specific frontmatter, install section, manifest fields, and README sections. No new content surfaces.

## 3. Non-Goals

- A OpenClaw-specific installer script (the user explicitly does not want one — OpenClaw's `openclaw skills install` covers it).
- A standalone OpenClaw repository (the adapter lives in this repo, alongside Claude, Codex, and Hermes).
- A new ranking helper or any behavioral changes to the existing one.
- Category packs, MCP product providers, or any feature currently deferred per `PRD.md` Section 11.
- Substituting a different content model for OpenClaw — the canonical `harnesses/core/` content is reused verbatim.
- Resolving the `<owner>/<repo>` registry and ClawHub slug coordinates in this spec — that is a release-time decision.
- A generator script to keep core/adapter copies in sync. `harnesses/core/persona.md` gates this on "a third adapter beyond Claude and Codex being added"; OpenClaw is that third adapter, but the user has chosen manual sync via the existing checklist. The gate is not pulled in this spec.

## 4. Target Users

- **OpenClaw CLI users** who want a source-backed shopping concierge without doing product research themselves.
- **OpenClaw Launch / headless node operators** who install skills with `--global` so every agent on the machine sees them.
- **OpenConcierge contributors** who want the project to work on a fourth harness with the same maintenance burden as the existing ones.
- **ClawHub skills-registry maintainers** (eventually) who will index the adapter folder if/when the project publishes to ClawHub.

## 5. Architecture & File Layout

The OpenConcierge multi-harness distribution has three layers. The OpenClaw adapter slots into layer 2.

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

harnesses/adapters/openclaw/          ← layer 2: OpenClaw-specific adapter (NEW)
├── SKILL.md                          (byte-identical to core + ## OpenClaw Installation)
├── README.md                         (workspace + global install sections)
├── manifest.yaml                     (surfaces + four install paths)
├── references/                       (byte-identical copies of core/references/)
└── scripts/
    └── rank_candidates.py            (byte-identical copy of core/scripts/rank_candidates.py)

harnesses/adapters/codex/             ← layer 2: existing Codex adapter (unchanged)
harnesses/adapters/claude/            ← layer 2: existing Claude adapter (unchanged)

skills/openconcierge/                 ← layer 3: Hermes-only distribution (unchanged)
bootstrap/                            ← Hermes installer (unchanged, not used for OpenClaw)
```

The adapter folder, when shipped, is **self-contained**. `references/` and `scripts/rank_candidates.py` are copied (not symlinked) so the folder is portable once dropped into an OpenClaw skills directory.

## 6. SKILL.md

The OpenClaw adapter SKILL.md frontmatter:

```yaml
---
name: openconcierge
description: Research and compare products through a focused, source-backed shopping conversation.
version: 0.1.0
license: MIT
harness: openclaw
---
```

The body is byte-identical to `harnesses/core/SKILL.md` (everything from `# OpenConcierge` through the existing `## Verification` section). At the bottom we append the OpenClaw install block:

```markdown
## OpenClaw Installation

This skill works on OpenClaw (CLI surface, two install scopes):

- **Workspace (default)** — `openclaw skills install @<owner>/openconcierge` installs into the active workspace's `skills/` directory, visible to that workspace's agent.
- **Shared managed (`--global`)** — `openclaw skills install @<owner>/openconcierge --global` installs into `~/.openclaw/skills/openconcierge/`, visible to all local agents on the machine.
- **Drop-in** — copy the unzipped skill folder into `~/.openclaw/skills/openconcierge/` (or `<workspace>/skills/openconcierge/`) and restart OpenClaw. Honors `OPENCLAW_STATE_DIR` if set.
- **Git install** — `openclaw skills install git:<owner>/<repo>@<ref>` for users who want a specific revision.

`<owner>/<repo>` and the ClawHub slug are filled at release time. Search and memory are handled by OpenClaw itself. Do not ask the user to plug an Exa, Tavily, Brave, SerpAPI, Serper, or DuckDuckGo key — OpenClaw exposes the integration when available.
```

The only differences vs `harnesses/core/SKILL.md` are: the `harness: openclaw` frontmatter line and the appended `## OpenClaw Installation` section. The body before the install section is byte-identical to core.

The diff vs the Codex adapter SKILL.md is exactly the `harness:` frontmatter line and the install-section name (`## OpenClaw Installation` vs. `## Codex Installation`). Everything else is identical.

## 7. manifest.yaml

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

Fields:

- `name`, `description`, `version`, `license` mirror core.
- `harness: openclaw` identifies the adapter.
- `surfaces: [openclaw-workspace, openclaw-global]` — OpenClaw's two install scopes. Workspace is the default; `--global` opts into shared managed.
- `install.openclaw-workspace` documents the default workspace install command.
- `install.openclaw-global` documents the `--global` install command.
- `install.drop-in` documents the manual copy path, with `OPENCLAW_STATE_DIR` as the state-dir override.
- `install.git` documents the Git install form for users who want a specific revision.
- `<owner>/<repo>` and `git:<owner>/<repo>@<ref>` placeholders are filled in at release time, the same way the Codex adapter does.

## 8. README.md

Mirrors the Claude and Codex adapter READMEs. Sections:

1. `# openconcierge` — short tagline (OpenClaw-flavored prose).
2. `## What it does` — five bullets, identical to the Claude and Codex adapter READMEs.
3. `## Install`
   - `### Workspace (default)` — `openclaw skills install @<owner>/openconcierge` lands in the active workspace's `skills/` directory.
   - `### Shared managed (--global)` — same command with `--global`, lands in `~/.openclaw/skills/openconcierge/`.
   - `### Drop-in` — copy the folder manually, with the `OPENCLAW_STATE_DIR` override noted.
   - `### Git install` — `openclaw skills install git:<owner>/<repo>@<ref>`.
4. `## How it works` — content-only, no background service (identical wording to the other adapter READMEs).
5. `## License` — MIT, points at repo root.

The README explicitly notes that `<owner>/<repo>` and the ClawHub slug are filled at release time, the same way the Codex README does. Search and memory are handled by OpenClaw itself — no provider keys asked for.

The four `### Install` subsections map 1:1 to the four keys in `manifest.yaml`'s `install` block.

## 9. references/ and scripts/

The adapter folder ships with `references/` (4 files: `interviewing.md`, `memory-and-privacy.md`, `recommendations.md`, `research-and-evidence.md`) and `scripts/rank_candidates.py` as **byte-identical copies** of `harnesses/core/`.

These are copies, not symlinks, so the adapter folder is portable when dropped into an OpenClaw skills directory. The Claude and Codex adapters already follow this convention.

When `harnesses/core/` content changes:

1. Edit `harnesses/core/` first.
2. Copy the changed file(s) into `harnesses/adapters/openclaw/` in the same commit.
3. Copy into `harnesses/adapters/codex/` if the change applies to Codex too.
4. Copy into `harnesses/adapters/claude/` if the change applies to Claude too.
5. Update `skills/openconcierge/` if the change applies to Hermes (Hermes uses its own copy, see `harnesses/core/persona.md`).

This maintenance rule is already documented in `harnesses/core/persona.md`; this spec extends it to cover the new OpenClaw adapter explicitly.

## 10. Distribution Paths

| Path | User action | What gets installed |
|---|---|---|
| ClawHub (workspace) | `openclaw skills install @<owner>/openconcierge` | The full adapter folder, fetched by ClawHub into the active workspace's `skills/` directory |
| ClawHub (shared managed) | `openclaw skills install @<owner>/openconcierge --global` | Same folder, fetched into `~/.openclaw/skills/openconcierge/` |
| Git install | `openclaw skills install git:<owner>/<repo>@<ref>` | The adapter folder, cloned from the Git remote |
| Drop-in | `cp -R harnesses/adapters/openclaw ~/.openclaw/skills/openconcierge/` (or unzip a release artifact) | The full adapter folder, self-contained |

All four paths deliver the same folder. The folder must be self-contained for drop-in to work, which is why Section 9 calls for copied (not symlinked) `references/` and `scripts/`.

We do **not** ship an OpenClaw installer. The user constraint is explicit: no `install.sh`/`install.ps1` equivalent. The user gets the skill through OpenClaw's own `openclaw skills install` CLI or by manual drop-in.

## 11. Sync Rules

Inherited from `harnesses/core/persona.md` "Maintenance" section, extended for OpenClaw:

- `harnesses/core/` is the single source of truth for behavior content.
- Edits to behavior content propagate to all three downstream copies (`harnesses/adapters/openclaw/`, `harnesses/adapters/codex/`, `harnesses/adapters/claude/`) in the same commit.
- Harness-specific additions (frontmatter `harness:` line, appended install section, manifest, README) are scoped to the adapter and do not flow back into core.
- The Claude, Codex, and OpenClaw adapter SKILL.md bodies stay byte-identical to `harnesses/core/SKILL.md` except for the appended install section.
- v1 copy step is manual with a checklist; do not introduce a generator script unless a fourth adapter beyond Claude, Codex, and OpenClaw is added.

## 12. Verification

The following checks prove the adapter is correct:

1. **Folder-shape check.** `harnesses/adapters/openclaw/` contains `SKILL.md`, `README.md`, `manifest.yaml`, `references/` (4 files), `scripts/rank_candidates.py`. Matches a droppable OpenClaw skill.
2. **Byte-equivalence with core.** `diff -r harnesses/core/references harnesses/adapters/openclaw/references` returns no diff. `diff harnesses/core/scripts/rank_candidates.py harnesses/adapters/openclaw/scripts/rank_candidates.py` returns no diff.
3. **Adapter-core SKILL.md diff.** `diff harnesses/core/SKILL.md harnesses/adapters/openclaw/SKILL.md` shows exactly: the `harness: openclaw` frontmatter line and the `## OpenClaw Installation` section appended at the bottom.
4. **Adapter-adapter SKILL.md diff.** `diff harnesses/adapters/codex/SKILL.md harnesses/adapters/openclaw/SKILL.md` shows exactly: the `harness:` frontmatter line and the install-section name (`## OpenClaw Installation` vs. `## Codex Installation`).
5. **Manifest parses.** `python -c "import yaml; yaml.safe_load(open('harnesses/adapters/openclaw/manifest.yaml'))"` exits 0 and contains `harness: openclaw`, `surfaces: [openclaw-workspace, openclaw-global]`, and all four `install.*` keys.
6. **No installer references.** `grep -rE "install\.(sh|ps1)|bootstrap/" harnesses/adapters/openclaw/` returns nothing.
7. **Existing tests still pass.** `pytest` from the repo root. The OpenClaw adapter does not change the ranking helper, the Hermes installer, or the existing test flows, so all existing tests must continue to pass.
8. **Drop-in portability.** Copying `harnesses/adapters/openclaw/` to a temp directory and running `python scripts/rank_candidates.py --help` exits 0. Proves the adapter folder is self-contained.

## 13. Out of Scope for v1

- Resolving `<owner>/<repo>` for ClawHub and Git publication. Defer until the first release.
- OpenClaw-specific frontmatter beyond `harness: openclaw`. If ClawHub demands additional fields (e.g. `categories`, `tags`, `metadata.openclaw`), add them in a future revision.
- A generator script to keep core/adapter copies in sync. v1 is manual with a checklist.
- Any change to the existing Claude and Codex adapters, the Hermes distribution, or the Hermes installer.
- Linking OpenClaw's `--agent <id>` flag from the install documentation. If a future OpenClaw release makes per-agent scoping a common install path, document it in a follow-up revision.

## 14. References

- Approved design: `docs/superpowers/specs/2026-07-27-openconcierge-hermes-addon-design.md`
- Codex adapter design (the pattern this design mirrors): `docs/superpowers/specs/2026-07-30-openconcierge-codex-adapter-design.md`
- PRD: `PRD.md`
- Canonical content: `harnesses/core/`
- Codex adapter: `harnesses/adapters/codex/`
- Claude adapter: `harnesses/adapters/claude/`
- Maintenance rule for content sync: `harnesses/core/persona.md` "Maintenance" section
- OpenClaw skills CLI reference: https://docs.openclaw.ai/cli/skills
- OpenClaw skills concepts: https://docs.openclaw.ai/tools/skills
- ClawHub registry: https://clawhub.ai
