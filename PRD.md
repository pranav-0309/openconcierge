# PRD: OpenConcierge — Source-Backed Shopping Concierge for Hermes Agent

> **Status:** Approved. Aligned with the approved design at `docs/superpowers/specs/2026-07-27-openconcierge-hermes-addon-design.md` and the implementation plans under `docs/superpowers/plans/`.

## 1. Overview

**Product name:** OpenConcierge.

**One-liner:** An open-source Hermes Agent profile distribution and skill that interviews users about what they want to buy, researches the live web through whatever search integration the user's Hermes profile already exposes, and recommends the best product for their needs and budget.

**Inspiration:** Zamana, a personal shopping assistant currently offered on iMessage, which chats with users, asks clarifying questions, and does deep research to find the right product at the right price.

**Core differentiator:** OpenConcierge is a Hermes-native add-on. Hermes owns the model, the gateways, the memory, the search backends, MCP, sessions, profiles, and the desktop UI. OpenConcierge owns only the shopping conversation, evidence rules, deterministic ranking, and a guided installer. Users pick up OpenConcierge the same way they pick up any Hermes skill — without forking, hosting, or replacing Hermes.

## 2. Goals

- Make it possible for a non-technical user to add a source-backed shopping concierge to Hermes with a single command on Windows, macOS, or Linux.
- Elicit real user needs through conversation instead of requiring structured search forms.
- Research the live web through the user's existing Hermes search configuration and rank products with a transparent, deterministic scoring rule.
- Persist stable shopping preferences so future tasks can skip redundant questions, with user-controlled view, correct, and forget flows.
- Reuse any compatible search integration already exposed by Hermes — Hermes web search, Hermes web extract, an installed fallback search skill, or any discoverable MCP/plugin search tool — without configuring a provider inside OpenConcierge.

## 3. Non-Goals (v1)

OpenConcierge will not include any of the following in v1. Each is gated on a measured failure of the native design.

- A separate OpenConcierge desktop, web, or mobile application. Hermes Desktop is the everyday UI.
- A standalone OpenConcierge backend or agent loop. OpenConcierge runs inside the user's Hermes profile.
- A custom chat gateway or messaging-channel adapter. Hermes owns channels.
- A web chat implementation, browser extension, or webhook receiver.
- An OpenConcierge-owned LLM-provider abstraction, `LLMProvider`, `SearchProvider`, or `ProductProvider` interface.
- A hosted product-search API integration, MCP server, or background sidecar.
- A custom OpenConcierge database, vector store, memory service, or telemetry service.
- Product-scraping infrastructure, affiliate links, checkout, payments, or inventory guarantees.
- Category-specific question packs ("pillow pack", "laptop pack", etc.).
- WhatsApp onboarding, Telegram-bot setup automation beyond a printed handoff message, or async research workers.
- A token-cost dashboard or per-task cost counter.
- A fixed maximum number of clarifying questions.

## 4. Target Users

- **End users:** People who want expert-level shopping research without doing it themselves — for example finding the right pillow, laptop, mattress, or gift. They reach OpenConcierge through whichever Hermes channel they already use (Telegram, Discord, Slack, WhatsApp, etc.) or directly inside Hermes Desktop.
- **Self-hosters / operators:** Hermes users who want a shopping-focused profile alongside their existing profile. They pick "Dedicated concierge" or "Add shopping to my current agent" during installation.
- **Contributors:** Open-source developers who want to extend OpenConcierge with category packs, additional reference fixtures for the ranking helper, or installer improvements. Core shopping behavior stays in the official distribution.

## 5. Core User Story

> "I'm trying to find a new pillow because the one I'm using hurts my neck, I'm not getting sleepy easily with it, and it's always hot."

OpenConcierge should:

1. Parse the message into a structured in-conversation shopping brief (category, problems, must-haves, preferences, avoid list, budget, region).
2. Ask follow-up questions whose answers can change eligibility, ranking, budget, region, safety, or product type. Stop asking once a useful search is possible. Accept "use your judgment" and treat revisions at any time.
3. Research the live web through whatever search capability the user's Hermes profile already exposes. OpenConcierge never requests a specific provider.
4. Verify each shortlisted candidate against a direct product or manufacturer page when possible and label inaccessible, stale, conflicting, or absent facts as unknown.
5. Apply hard filters (maximum budget, regional availability, explicit exclusions, must-have features, delivery deadlines) before scoring.
6. Rank the remaining candidates with a transparent weighted scoring rule (`strong`/`partial`/`none`/`unknown` × `must`/`core`/`preference`/`nice`) and present 2–4 sourced options with rationale, trade-offs, unverified details, and direct links.
7. Persist confirmed stable preferences (preferred brands, common sizing, region, currency, budget sensitivity) for future tasks and never auto-persist sensitive health, allergy, or disability constraints.

## 6. System Architecture

### 6.1 Ownership boundary

Hermes Agent owns:

- The desktop, CLI, TUI, and messaging interfaces.
- LLM provider configuration and model routing.
- Search backends (canonical web search, web extract), MCP servers, and progressive tool discovery.
- Profiles, sessions, memory, and state.
- Gateway processes and channel adapters.
- Skill discovery, installation, and updates.
- Provider credentials and secret storage.

OpenConcierge owns:

- The OpenConcierge persona (`SOUL.md`) for the dedicated profile.
- The provider-neutral `openconcierge` skill (`SKILL.md`) and four reference documents.
- The deterministic ranking helper (`skills/openconcierge/scripts/rank_candidates.py`).
- The guided installer (`bootstrap/install.sh` for macOS/Linux, `bootstrap/install.ps1` for Windows) plus the release-manifest generator.
- The release manifest (`bootstrap/release.json`) that ships distribution and skill source URLs.

OpenConcierge will not fork, embed, proxy, or recreate the Hermes runtime.

### 6.2 High-level diagram

```text
Hermes Desktop / CLI / TUI / configured gateway
                         |
                 Hermes profile
          (SOUL + OpenConcierge skill)
                         |
        Hermes model, memory, and tool registry
                         |
   canonical search | fallback skill | MCP/plugin search
```

### 6.3 Components

| Owner | Component | Responsibility |
|---|---|---|
| Hermes | Desktop / CLI / TUI / gateway | All chat-platform surfaces |
| Hermes | Model routing and credentials | LLM provider configuration |
| Hermes | Canonical search, MCP, plugin tools | Any search capability already visible to the profile |
| Hermes | Profiles, sessions, memory | Persistent and in-conversation state |
| Hermes | Skill discovery, install, update | Where OpenConcierge ships |
| OpenConcierge | `distribution.yaml` | Hermes profile-distribution manifest, ownership boundary |
| OpenConcierge | `SOUL.md` | Dedicated profile identity, safety commitments |
| OpenConcierge | `skills/openconcierge/SKILL.md` | Provider-neutral skill entry point |
| OpenConcierge | `skills/openconcierge/references/` | Interviewing, research/evidence, recommendation, memory/privacy |
| OpenConcierge | `scripts/rank_candidates.py` | Deterministic ranking and filtering |
| OpenConcierge | `bootstrap/install.sh` and `install.ps1` | Cross-platform guided installer |
| OpenConcierge | `bootstrap/build-release-manifest.py` | Release-manifest generator |
| OpenConcierge | `bootstrap/release.json` (generated at release time, not committed) | Distribution and skill source URLs |

## 7. Functional Requirements

1. **Guided setup for users with or without Hermes on Windows, macOS, and Linux.** The installer detects Hermes, hands off to the official Hermes installation when needed, and never modifies Hermes internals.
2. **Dedicated-profile installation through a Hermes profile distribution.** Creates an isolated OpenConcierge personality and memory space via `hermes profile install` and `distribution_owned`.
3. **Existing-profile installation through the OpenConcierge skill alone.** Preserves the user's identity, provider, memory, and gateway configuration.
4. **Unlimited but decision-relevant clarifying questions.** Stop asking once a useful search is possible. Accept "use your judgment" and allow mid-task revisions.
5. **Provider-neutral search resolution.** Prefer Hermes `web_search`, use `web_extract` when available, then progressive MCP/plugin tool discovery, then an installed fallback search skill. Never require a specific provider or API key.
6. **Source-backed candidate evidence and deterministic filtering and ranking.** Hard filters, weighted soft scoring, source-URL requirements, and unknown-aware output.
7. **Recommendation trade-offs, uncertainty, and observed dates.** Never fabricate products, prices, availability, ratings, or specifications.
8. **Explicit-confirmation preference memory with namespaced deletion.** Support `show preferences`, `correct preference`, `forget preference`, and `forget all preferences`. Do not auto-persist sensitive health, allergy, or disability constraints.
9. **Passive installation verification.** No model prompt, web search, gateway launch, or credential read at install time. Installation and updates do not transmit or log credentials.
10. **Clear failure behavior.** No fabricated results. When no compatible search capability exists, direct the user to Hermes Desktop tools/skills/MCP settings without prescribing a provider.

## 8. Non-Functional Requirements

- **NFR1 (Hermes-native self-hosting).** No OpenConcierge-managed cloud service is required. Operators install Hermes and then OpenConcierge; both run locally.
- **NFR2 (Credentials stay in Hermes).** OpenConcierge never reads, writes, or transmits credentials. Bootstrap logs and installer scripts redact any secret-shaped value.
- **NFR3 (Source-of-truth comes from official Hermes installers).** Bootstrap downloads only from `https://hermes-agent.nousresearch.com/`. The OpenConcierge distribution is fetched from a release-operator-controlled git or HTTP source recorded in `bootstrap/release.json`.
- **NFR4 (Testability without live providers).** Ranking, installer state, and skill behavior are testable with mocked providers and a fake Hermes CLI. No unit test makes a network call.
- **NFR5 (Privacy).** No third-party telemetry. Stable shopping preferences live in Hermes memory and can be deleted at any time.
- **NFR6 (Determinism).** Ranking output is stable for identical input. Sort order is `fit_score desc → price asc → case-insensitive name → URL`.
- **NFR7 (Portability).** The installer runs on Windows (PowerShell 7), macOS, and Linux (Bash) from the same source. Exit codes are stable: 0 success, 2 cancellation, 3 command failure, 4 registration failure.

## 9. Data Model

OpenConcierge does not own a database. The structured shapes below are in-conversation working state and Hermes memory entries.

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

### 9.3 Persistent preferences (Hermes memory only)

- Preferred or avoided brands, common sizing, budget sensitivity, preferred materials, region, currency, recurring compatibility constraints.
- Confirmation-gated. Sensitive health, allergy, or disability constraints are used for the current task only unless the user explicitly asks for persistent storage.

## 10. Provider Strategy

OpenConcierge exposes no provider interface. Search capability is selected at runtime by Hermes from the active profile's existing configuration:

1. Hermes `web_search` first, honoring the configured backend (Exa, Tavily, Brave, DuckDuckGo, SearXNG, Firecrawl, Parallel, xAI, etc.).
2. Hermes `web_extract` when available for direct product-page verification.
3. Progressive MCP/plugin tool discovery for any compatible search tool the user has installed.
4. An installed fallback search skill if Hermes surfaces one.
5. One already-configured fallback after a search failure. Never fan out across every provider.

OpenConcierge never asks for a provider API key that Hermes has already configured. OpenConcierge never duplicates provider configuration.

## 11. Milestones

- **M1: Core profile distribution, shopping skill, and deterministic ranking.** Done.
- **M2: Existing-profile skill installation and preference controls.** Done.
- **M3: Cross-platform guided bootstrapper and official Hermes handoff.** Done.
- **M4: Clean-machine validation and release hardening.** In progress.

Deferred expansions, each gated on a measured failure of the native design:

- MCP product provider, only if web research repeatedly fails to provide sufficiently current or structured product evidence.
- Category packs, only if general-product evaluations show recurring category-specific questioning failures.
- Custom memory layer, only if Hermes memory cannot support accurate view, correction, and deletion of shopping preferences.
- WhatsApp-specific onboarding, only after the Telegram and Desktop paths are reliable.
- Affiliate links, only after a disclosure policy and user-value case are approved.

## 12. Open Questions (re-scoped)

The original PRD's open questions assumed OpenConcierge-owned provider adapters. With the ownership boundary in Section 6, those questions become:

- What is the minimum set of Hermes provider configurations that should be exercised before declaring v1 ready? (Documented in `docs/superpowers/plans/2026-07-27-openconcierge-bootstrap-plan.md` and the roadmap's release-hardening phase.)
- When should OpenConcierge publish a Hermes skill-only release in addition to the profile distribution? (M2 already covers this.)
- How should the project handle regions with no public product-search API? (Documented: OpenConcierge relies on the user's Hermes search configuration; if no compatible capability exists, OpenConcierge reports it honestly rather than scraping.)
- Should community-contributed category packs ship as separate skill directories? (Deferred until M4 evidence justifies them.)

## 13. Success Metrics (v1)

- Time from first message to first product shortlist in supported categories.
- Percentage of shopping tasks completed without the user abandoning the conversation.
- Number of clarifying questions asked per task, trending down as preferences persist.
- Number of clean-machine installations completed without manual YAML editing on Windows, macOS, and Linux.

## 14. References

- Approved design: `docs/superpowers/specs/2026-07-27-openconcierge-hermes-addon-design.md`
- Implementation plans: `docs/superpowers/plans/2026-07-27-openconcierge-core-distribution-plan.md`, `docs/superpowers/plans/2026-07-27-openconcierge-bootstrap-plan.md`, `docs/superpowers/plans/2026-07-27-openconcierge-implementation-roadmap.md`
- Hermes Agent installation: https://hermes-agent.nousresearch.com/docs/getting-started/installation
- Hermes Desktop: https://hermes-agent.nousresearch.com/docs/user-guide/desktop
- Hermes profiles: https://hermes-agent.nousresearch.com/docs/user-guide/profiles
- Hermes profile distributions: https://hermes-agent.nousresearch.com/docs/user-guide/profile-distributions
- Hermes skills: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
