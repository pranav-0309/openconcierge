# PRD: Shopping Concierge Skill for AI

## 1. Overview

**Product name:** OpenConcierge.

**One-liner:** An open-source shopping concierge skill that can be added to any AI product with a skill-loading mechanism — Claude, ChatGPT, Codex, OpenCode, Hermes Agent, OpenClaw, and any and all other AI products — that interviews users about what they want to buy, researches the live web through whatever search capability the host AI already exposes, and recommends the best product for their needs and budget.

**Inspiration:** Zamana, a personal shopping assistant currently offered on iMessage, which chats with users, asks clarifying questions, and does deep research to find the right product at the right price.

**Core differentiator:** OpenConcierge is a host-agnostic skill. The host AI owns the model, the interfaces, the memory, the search tools, and the runtime. OpenConcierge owns only the shopping conversation, evidence rules, and deterministic ranking. Users add OpenConcierge to whichever AI they already use — without forking, hosting, or replacing anything.

## 2. Goals

- Make it possible for a non-technical user to add a source-backed shopping concierge to any AI they already use, by loading the skill.
- Elicit real user needs through conversation instead of requiring structured search forms.
- Research the live web through the host AI's existing search capability and rank products with a transparent, deterministic scoring rule.
- Persist everything the skill learns about the user — including stable shopping preferences and relevant health, allergy, or disability context — so future recommendations are as tailored as possible, writing to whatever memory the host exposes.
- Work with any compatible search integration the host AI already exposes — built-in web search, web extraction, or any discoverable MCP/plugin search tool — without configuring a provider inside OpenConcierge.

## 3. Non-Goals (v1)

OpenConcierge will not include any of the following in v1. Each is gated on a measured failure of the skill-first design.

- A separate OpenConcierge desktop, web, or mobile application. The host AI's everyday interface is the UI.
- A standalone OpenConcierge backend or agent loop. OpenConcierge runs inside the host AI's session.
- A custom chat gateway or messaging-channel adapter. The host owns channels.
- A web chat implementation, browser extension, or webhook receiver.
- An OpenConcierge-owned LLM-provider abstraction, `LLMProvider`, `SearchProvider`, or `ProductProvider` interface.
- A hosted product-search API integration, MCP server, or background sidecar.
- A custom OpenConcierge database, vector store, memory service, or telemetry service.
- Product-scraping infrastructure, affiliate links, checkout, payments, or inventory guarantees.
- Category packs. The skill is one general-product skill, permanently.
- Deleting or modifying host memories that are unrelated to shopping. The skill only writes to memory; it never asks the host to delete the user's other memories.
- A token-cost dashboard or per-task cost counter.
- A fixed maximum number of clarifying questions.

## 4. Target Users

- **End users:** People who want expert-level shopping research without doing it themselves — for example finding the right pillow, laptop, mattress, or gift. They reach OpenConcierge through whichever AI product they already use, on any channel that product supports.
- **Operators / self-hosters:** People who manage their own AI setups and want to add shopping capability to an existing agent without changing its identity, providers, or memory.
- **Contributors:** Open-source developers who want to extend OpenConcierge with host-specific packaging or new host integrations. Core shopping behavior stays in the official distribution.

## 5. Core User Story

> "I'm trying to find a new pillow because the one I'm using hurts my neck, I'm not getting sleepy easily with it, and it's always hot."

OpenConcierge should:

1. Parse the message into a structured in-conversation shopping brief (category, problems, must-haves, preferences, avoid list, budget, region).
2. Ask follow-up questions whose answers can change eligibility, ranking, budget, region, safety, or product type. Stop asking once a useful search is possible. Accept "use your judgment" and treat revisions at any time.
3. Research the live web through whatever search capability the host AI already exposes. OpenConcierge never requests a specific provider.
4. Verify each shortlisted candidate against a direct product or manufacturer page when possible and label inaccessible, stale, conflicting, or absent facts as unknown.
5. Apply hard filters (maximum budget, regional availability, explicit exclusions, must-have features, delivery deadlines) before scoring.
6. Rank the remaining candidates with a transparent weighted scoring rule (`strong`/`partial`/`none`/`unknown` × `must`/`core`/`preference`/`nice`) and present 2–4 sourced options with rationale, trade-offs, unverified details, and direct links.
7. Persist everything learned about the user — shopping preferences and relevant personal context alike — to whatever memory the host exposes, so future recommendations are as tailored as possible. The skill only writes to memory; it never deletes or modifies host memories unrelated to shopping.
8. Invite feedback lightly. When presenting recommendations, the skill adds a brief note asking the user to let it know if they buy any of these and whether it worked out / whether the concierge helped. No proactive follow-ups afterwards. When the user later mentions — unprompted — that something they were recommended worked or didn't, the skill records the outcome and uses it to shape future recommendations.

## 6. System Architecture

### 6.1 Ownership boundary

The host AI owns:

- All chat surfaces (desktop, web, CLI, mobile, and messaging channels).
- LLM provider configuration and model routing.
- Search backends, web extraction tools, MCP servers, and progressive tool discovery.
- Sessions, memory, and state.
- Skill discovery, installation, and updates.
- Provider credentials and secret storage.

OpenConcierge owns:

- The provider-neutral `openconcierge` skill (`SKILL.md`) and four reference documents.
- The scoring and ranking rules, fully specified in prose so any host can apply them without code execution.
- The deterministic ranking helper (`rank_candidates.py`) — a mandatory deliverable of the project — for hosts that can execute scripts.
- The repository layout, the `.claude-plugin/marketplace.json` manifest, and the packaging/publishing pipeline that give the skill day-1 install compatibility across all major AI products.

OpenConcierge will not fork, embed, proxy, or recreate any host runtime.

### 6.2 High-level diagram

```text
Any AI host (Claude, ChatGPT, Codex, OpenCode, Hermes Agent, OpenClaw, ...)
          (desktop / web / CLI / messaging surfaces)
                          |
                 Host profile or session
          (existing identity + OpenConcierge skill)
                          |
      Host model, memory, and tool registry
                          |
   built-in search | web extraction | MCP/plugin search
```

### 6.3 Repository layout (day-1 compatibility)

The repository follows the cross-agent skills convention so every major agent installs it natively, with zero user-side fixes:

```text
open-concierge/
├── .claude-plugin/
│   └── marketplace.json        # enables Claude Code's native /plugin installer
├── skills/                     # the ONE canonical skills folder
│   └── openconcierge/
│       ├── SKILL.md            # required — exact casing, at skill folder root
│       ├── scripts/
│       │   └── rank_candidates.py
│       └── references/
│           ├── interviewing.md
│           ├── research-evidence.md
│           ├── recommendation.md
│           └── memory-privacy.md
├── README.md
├── LICENSE
└── CHANGELOG.md
```

Hard rules for this layout:

1. One folder per skill, under `skills/`. Two-level categorization is allowed (`skills/<category>/<name>/SKILL.md`) but never deeper, and never nest a skill inside another skill.
2. No per-agent copies inside the repo (`.claude/skills/`, `.codex/`, `.opencode/`, `.agents/`, `.hermes/`, etc.). Installers handle per-agent placement; duplicate folders cause double discovery.
3. `.claude-plugin/marketplace.json` is the only agent-specific addition — a manifest, not a copy of the skills. It also enables claude.ai org "Sync from GitHub" and is read by the `npx skills` CLI during discovery.
4. Every skill folder must be fully self-contained and zippable on its own, with no references to files outside its own folder.
5. `SKILL.md` frontmatter must carry `name` (lowercase-hyphen, matching the folder name, ≤ 64 chars) and `description`. No `context: fork`, no `hooks:` — shared skills must not use them.
6. `SKILL.md` carries a `version` field and the README lists the current release, because upload-based hosts (ChatGPT, claude.ai/Desktop) never receive automatic updates — users need a way to notice they're outdated.

### 6.4 Installation matrix (all work with this exact structure)

| Host | Native install method | Destination |
|---|---|---|
| Any (universal) | `npx skills add <owner>/<repo>` (auto-detects installed agents; supports `--skill`, `-a <agent>`, `--list`) | Each agent's native dir |
| Claude Code | `/plugin marketplace add <owner>/<repo>` → `/plugin install open-concierge`, or copy skill folder into `~/.claude/skills/` (global) or `.claude/skills/` (project) | `~/.claude/skills/`, `.claude/skills/` |
| claude.ai / Claude Desktop | Upload a ZIP of the skill folder (folder at zip root) via Settings → Customize → Skills → Upload | Web/desktop skill list |
| ChatGPT (web) | Profile icon → Skills → New skill → Upload from computer → select `SKILL.md` or the skill-folder ZIP | ChatGPT skill list |
| Codex | Copy skill folder into `~/.codex/skills/` (global) or `.codex/skills/` / `.agents/skills/` (project); in-session: `$skill-installer install <repo-url>/tree/main/skills/openconcierge` | `~/.codex/skills/`, project dirs |
| OpenCode | Copy skill folder into `.opencode/skills/`, `.agents/skills/`, or `.claude/skills/` (project); `~/.config/opencode/skills/` (global) | Project + global dirs |
| Hermes Agent | `hermes skills install <raw-SKILL.md-url>`, or `/skills install <identifier>` in chat; teams: `HERMES_OPTIONAL_SKILLS_DIR` pointing at the repo's `skills/` | `~/.hermes/skills/` |
| OpenClaw | `openclaw skills install skills-sh:<owner>/<repo>/<slug>` or `npx clawhub@latest install --git <repo-url>.git`; after ClawHub publishing: `openclaw skills install @<owner>/<slug>` | workspace `skills/` or `~/.openclaw/skills/` |
| Cursor / Copilot / Cline / Gemini CLI | Copy skill folder into `.agents/skills/` (shared cross-agent convention) | `.agents/skills/` |

No restructuring is ever needed: every native method either copies a self-contained folder, fetches a URL pointing at a folder, or resolves a registry entry that wraps a folder. This layout satisfies all three shapes by default.

### 6.5 Components

| Owner | Component | Responsibility |
|---|---|---|
| Host | Chat surfaces | All user-facing conversation channels |
| Host | Model routing and credentials | LLM provider configuration |
| Host | Search, MCP, plugin tools | Any search capability already visible to the session |
| Host | Sessions and memory | Persistent and in-conversation state |
| Host | Skill loading | Where OpenConcierge runs |
| OpenConcierge | `skills/openconcierge/SKILL.md` | Provider-neutral skill entry point |
| OpenConcierge | `skills/openconcierge/references/` | Interviewing, research/evidence, recommendation, memory/privacy |
| OpenConcierge | `skills/openconcierge/scripts/rank_candidates.py` | Mandatory deliverable: deterministic ranking for hosts that can execute scripts; prose rules are the fallback when it can't run |
| OpenConcierge | `.claude-plugin/marketplace.json` | Claude Code plugin installer, claude.ai GitHub sync, `npx skills` discovery |
| OpenConcierge | README + release ZIPs | Per-skill upload packages for claude.ai / Claude Desktop / ChatGPT |

## 7. Functional Requirements

1. **Portable skill files in the cross-agent layout.** The skill ships under `skills/openconcierge/` in the repository structure defined in Section 6.3, with `SKILL.md` at the folder root and a fully self-contained folder that installs natively on every major agent without user-side fixes.
2. **Mandatory ranking script with a defined fallback.** The implementing agent must create `rank_candidates.py` and test it. It is used whenever the host can execute scripts. If the host cannot run it (for example ChatGPT or Claude web apps), the skill detects this and falls back to applying the same scoring and ranking rules from the prose specification in the reference documents — so recommendations are identical in method, only produced manually.
3. **Host-agnostic installation.** Adding the skill never requires a dedicated installer, never modifies host internals, and preserves the user's existing identity, providers, memory, and channels. Users install through each host's native mechanism (Section 6.4) or the universal `npx skills add` CLI.
4. **ZIP packaging for upload-based hosts.** Release artifacts zip THE skill folder, not its contents — `openconcierge/` must be the top-level entry inside the ZIP. Zips are built with `cd skills && zip -r ../dist/openconcierge.zip openconcierge/`, with credentials, caches, and `.git` removed first.
5. **Registry and marketplace publishing.** The repo is public so skills.sh indexes it automatically (`npx skills add <owner>/<repo>` and OpenClaw's `skills-sh:` install both resolve). `.claude-plugin/marketplace.json` enables Claude Code and claude.ai. ClawHub and Hermes Skills Hub publishing are required before the first GitHub release. GitHub Releases attach one per-skill ZIP per release for upload-based hosts.
6. **Unlimited but decision-relevant clarifying questions.** Stop asking once a useful search is possible. Accept "use your judgment" and allow mid-task revisions.
7. **Provider-neutral search resolution.** Use the host's built-in web search first, web page extraction when available, then any discoverable MCP/plugin search tool. Never require a specific provider or API key.
8. **Missing search capability handled conversationally.** If the host exposes no way to search the web, the skill tells the user honestly and asks them to provide some kind of search functionality — enabling a built-in tool or connecting an MCP search server. It never asks the user to paste research. However, if the user volunteers research unprompted, the skill accepts it and treats it as first-class evidence with full source-tracking. It never fabricates results in place of search.
9. **Source-backed candidate evidence with review skepticism.** Hard filters, weighted soft scoring, source-URL requirements, and unknown-aware output. Evidence rules down-weight affiliate-driven "best X" listicles and treat suspicious review patterns (thin review counts, uniformly glowing ratings, templated praise) as low-quality signals. Ratings from manufacturer or seller pages alone are never sufficient evidence.
10. **Recommendation trade-offs, uncertainty, and observed dates.** Never fabricate products, prices, availability, ratings, or specifications.
11. **Write-only preference and context memory, with self-correction.** Persist everything learned about the user — shopping preferences, relevant personal context, and purchase outcomes — to whatever memory the host exposes, using the host's own memory mechanism. The skill may update or correct its own prior shopping-related memory entries; it never deletes or modifies host memories unrelated to shopping.
12. **Lightweight post-recommendation feedback loop.** When presenting recommendations, the skill briefly asks the user to let it know if they buy any of them and whether it worked out. It never sends proactive follow-ups. When a user spontaneously reports an outcome — "the pillow you recommended worked great" or "I returned it, too firm" — the skill records what was bought and how it worked out, and uses that outcome to shape future recommendations in the same category.
13. **Clear failure behavior.** No fabricated results. When no compatible search capability exists, tell the user honestly and ask them to provide one, per requirement 8.

## 8. Non-Functional Requirements

- **NFR1 (Host-agnostic).** No OpenConcierge-managed cloud service is required. The skill runs wherever the host AI runs.
- **NFR2 (Credentials stay in the host).** OpenConcierge never reads, writes, or transmits credentials.
- **NFR3 (Testability without live providers).** Ranking and skill behavior are testable with mocked providers and scripted host sessions. No unit test makes a network call.
- **NFR4 (Privacy).** No third-party telemetry. Everything the skill learns lives in the host's own memory and is subject to the host's memory controls. The skill itself never deletes or modifies memories unrelated to shopping.
- **NFR5 (Determinism).** Ranking output is stable for identical input. Sort order is `fit_score desc → price asc → case-insensitive name → URL`.
- **NFR6 (Portability).** The skill is plain files with no host-specific code in the core. Host-specific behavior lives in packaging guides, not in the skill itself.

## 9. Data Model

OpenConcierge does not own a database. The structured shapes below are in-conversation working state and host memory entries.

### 9.1 Shopping brief (in-conversation)

```yaml
category: string
problem_to_solve: string
intended_user: string
must_haves: string[]
preferences: string[]
avoid: string[]
budget:
  minimum: number | null
  maximum: number | null
  currency: string | null
region: string | null
deadline: string | null
existing_context: string[]
```

### 9.2 Candidate evidence (in-conversation)

```yaml
candidate:
  name: string
  product_url: string
  seller_or_manufacturer: string
  observed_price: number | null
  currency: string | null
  observed_at: date
  ships_to_region: true | false | unknown
  criteria:
    - requirement: string
      importance: must | core | preference | nice
      match: strong | partial | none | unknown
      source_urls: string[]
  tradeoffs: string[]
```

### 9.3 Persistent preferences, personal context, and outcomes (host memory only)

- Everything the skill learns about the user: preferred or avoided brands, common sizing, budget sensitivity, preferred materials, region, currency, recurring compatibility constraints, relevant personal context such as health, allergy, or disability needs that shape product fit, and reported outcomes (what was bought, kept, returned, or disliked from its recommendations).
- Written to whatever memory the host exposes, using the host's own memory mechanism. The skill may update or correct its own prior shopping-related entries; it never deletes or modifies host memories unrelated to shopping.

## 10. Provider Strategy

OpenConcierge exposes no provider interface. Search capability is selected at runtime by the host from its existing configuration:

1. The host's built-in web search first, honoring whatever backend it is configured with.
2. Web page extraction when available, for direct product-page verification.
3. Any discoverable MCP/plugin search tool the user has installed.
4. One already-configured fallback after a search failure. Never fan out across every provider.

OpenConcierge never asks for a provider API key the host has already configured. OpenConcierge never duplicates provider configuration. If the host exposes no search capability at all, the skill tells the user honestly and asks them to provide one — enabling a built-in tool or connecting an MCP search server — and never fabricates results in its place. The skill never asks the user to paste research, but if the user volunteers research unprompted, it accepts it as first-class evidence with full source-tracking.

## 11. Milestones

- **M1: Core shopping skill and deterministic ranking.** Author `SKILL.md`, the four reference documents, the prose scoring specification, and the mandatory `rank_candidates.py`, with mocked tests for ranking. Planned.
- **M2: Cross-agent repository layout and packaging.** Stand up the Section 6.3 structure (`.claude-plugin/marketplace.json`, `skills/openconcierge/`), the release-ZIP pipeline, and `npx skills add` discovery. Planned.
- **M3: Host install validation.** Verify the Section 6.4 installation matrix end to end on the v1 validation set (Section 12): Claude (web and Desktop), ChatGPT (web), Codex, OpenCode, Hermes Agent, and OpenClaw — in that order — covering both script-capable and script-less hosts. Other hosts (Cursor, Copilot, Cline, Gemini CLI) are validated post-v1. Planned.
- **M4: Publish and release.** Publish to skills.sh, ClawHub, and the Hermes Skills Hub, run the release validation checklist (Section 14), and cut the first public release with per-skill ZIPs on GitHub Releases. Planned.

Deferred expansions, each gated on a measured failure of the skill-first design:

- MCP product provider, only if web research repeatedly fails to provide sufficiently current or structured product evidence.
- Affiliate links, only after a disclosure policy and user-value case are approved.

Note on memory: the skill instructs the AI to persist preferences, personal context, and reported outcomes to whatever memory the host exposes (FR 11–12), but memory persistence is explicitly NOT validated on any host. Hosts differ too widely in memory mechanisms and none is controlled by this project; the skill's memory behavior is best-effort per host and is not part of v1 validation or the definition of done.

## 12. Resolved Decisions

- **v1 validation set.** v1 is declared ready when the skill installs and completes a full shopping task on: Claude (web and Desktop), ChatGPT (web), Codex, OpenCode, Hermes Agent, and OpenClaw — in that order. Other hosts (Cursor, Copilot, Cline, Gemini CLI) ship with the same files but are validated post-v1. Memory persistence is not part of validation (see the note in Section 11).
- **Hosts without a native skill mechanism (Perplexity, etc.).** Not supported in v1. No packaging work for them.
- **No usable web search.** The skill is honest: it tells the user it cannot search and asks them to provide a search capability. It never proceeds with unverified or inaccurate information in place of search.
- **Category packs.** Dropped from the roadmap entirely. The skill ships as one general-product skill, permanently.
- **Registry publishing.** Publish to skills.sh (automatic), ClawHub, and the Hermes Skills Hub before the first GitHub release, so every clean install command works on day 1.

## 13. Success Metrics & Validation Protocol (v1)

There is no telemetry (NFR4) and the skill runs inside hosts the project does not control, so success is measured by a manual validation protocol run during M3 and before each release, with results published in the repo:

- A fixed set of scripted test shopping tasks (for example: pillow, laptop, gift) is executed end to end on each host in the v1 validation set. Recorded per task: time from first message to first shortlist, number of clarifying questions asked, and whether the task completed without the user having to intervene on skill mechanics.
- Second runs of the same tasks check whether the interview flow behaves consistently when the user restates known preferences in-conversation. (Cross-session memory is not measured — it is best-effort per host and out of validation scope, per Section 11.)
- `npx skills add <owner>/<repo> --list` shows the skill, and it installs with zero user-side fixes on every host in the Section 6.4 matrix.
- Recommendation quality is spot-checked: every recommended candidate has verifiable source URLs, correct hard-filter behavior (over-budget or excluded products never appear), and no fabricated facts.
- Number of supported AI products on which a user can complete a full shopping task without manual editing of skill files.

## 14. Release Validation Checklist

Run before every release:

- [ ] Skill folder name matches frontmatter `name`, lowercase-hyphen, ≤ 64 chars.
- [ ] `SKILL.md` (exact casing) exists at the skill folder root with `name` + `description` frontmatter and a `version` field matching the release.
- [ ] README lists the current release version.
- [ ] No `context: fork`, no `hooks:` in the skill.
- [ ] No skill nested inside another skill; nothing deeper than 2 category levels.
- [ ] No per-agent folder copies inside the repo.
- [ ] `.claude-plugin/marketplace.json` exists and is valid JSON.
- [ ] `npx skills add <owner>/<repo> --list` shows the skill.
- [ ] Each release ZIP has the skill folder at the zip root and uploads successfully to claude.ai (limit: 30 MB uncompressed).
- [ ] Scripts run with `python3`/`bash` and declare their dependencies.
- [ ] Release ZIPs contain no credentials, caches, or `.git` artifacts.