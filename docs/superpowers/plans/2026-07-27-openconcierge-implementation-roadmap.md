# OpenConcierge Implementation Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver OpenConcierge as a tested Hermes profile distribution with an optional existing-profile skill install and a guided cross-platform bootstrapper.

**Architecture:** Implement the shopping distribution and ranking subsystem first, then implement the bootstrapper as a thin caller of Hermes commands. The core plan owns all shopping behavior; the bootstrapper owns installation state and never embeds shopping logic. Hermes remains the runtime for models, search, memory, Desktop, sessions, and gateways.

**Tech Stack:** Markdown, YAML, Bash, PowerShell, Python 3.11 standard library, `unittest`, Hermes Agent CLI and Desktop.

---

## Plan set and execution order

Execute these files in order:

1. `docs/superpowers/plans/2026-07-27-openconcierge-core-distribution-plan.md`
2. `docs/superpowers/plans/2026-07-27-openconcierge-bootstrap-plan.md`
3. The PRD alignment task in this roadmap

The first plan produces a usable local Hermes distribution and standalone skill. The second plan installs those artifacts on clean machines. The third plan removes the stale standalone-platform assumptions from `PRD.md` after the implementation behavior is proven.

This workspace is not currently a Git checkout. Do not create commits during execution unless the user explicitly requests them.

## Shared file ownership

The core plan owns:

```text
distribution.yaml
SOUL.md
skills/openconcierge/
tests/test_distribution_layout.py
tests/test_no_secrets.py
tests/test_skill_contract.py
tests/test_rank_candidates.py
tests/fixtures/ranking/
```

The bootstrap plan owns:

```text
bootstrap/
tests/installer/
```

The PRD alignment task owns only:

```text
PRD.md
```

No plan may add a backend, database, web UI, MCP server, provider adapter, gateway adapter, or separate Desktop application.

## Phase 0: Confirm the approved boundary

- [ ] Read `docs/superpowers/specs/2026-07-27-openconcierge-hermes-addon-design.md` before changing code.
- [ ] Confirm that the implementation uses Hermes profile distributions and skills rather than a new runtime.
- [ ] Confirm that search resolution is provider-neutral: canonical Hermes search first, then discoverable MCP/plugin tools or fallback skills.
- [ ] Confirm that no installation test sends a model prompt or web request.
- [ ] Confirm that the repository has no existing package manager or code convention to preserve.

Run:

```text
python -m unittest discover -s tests -v
```

Expected before implementation: the command either reports no tests or fails because the planned test files do not yet exist. Do not treat that as a product failure; begin with the red tests in the core plan.

## Phase 1: Build the core distribution

Follow every task in `2026-07-27-openconcierge-core-distribution-plan.md`.

The phase is complete only when:

- `distribution.yaml` has the exact ownership boundary and no environment secrets.
- `SOUL.md` defines the dedicated shopping identity without changing Hermes behavior outside that profile.
- `SKILL.md` has no provider-specific `requires_tools` or `requires_toolsets` metadata.
- The skill explicitly supports canonical Hermes web search, `web_extract` when available, progressive MCP/plugin tool discovery, and installed fallback search skills.
- The skill allows unlimited necessary clarifying questions and has a clear stop rule.
- The ranking helper returns deterministic `ranked`, `unranked`, and `rejected` arrays.
- Hard constraints and source evidence are tested.
- Preference memory is opt-in and namespaced.
- The full standard-library test suite passes without network access.

Run at the phase boundary:

```text
python -m unittest discover -s tests -v
python -m py_compile skills/openconcierge/scripts/rank_candidates.py
```

Expected: all core tests pass and the Python compiler exits `0`.

## Phase 2: Build the bootstrapper

Follow every task in `2026-07-27-openconcierge-bootstrap-plan.md`.

The phase is complete only when:

- `bootstrap/install.sh` and `bootstrap/install.ps1` accept equivalent logical options.
- Existing Hermes detection runs `hermes doctor` before modifying a profile.
- Missing Hermes is handed to the official Hermes installer over HTTPS, then Desktop is launched via Hermes.
- Dedicated mode uses supported profile clone/install commands and does not call `profile use`.
- Existing mode uses only the supported skill installer and never changes `SOUL.md`, provider settings, memory configuration, or gateways.
- A profile token conflict is surfaced rather than copied or silently started.
- Search capability checks recognize canonical web tools and discoverable custom/MCP signals without requiring a provider name.
- Missing search capability is a warning, not a forced provider installation.
- Cancellation, source errors, command failures, profile collisions, and passive validation have stable exit codes.
- Shell and PowerShell tests use fake commands and never contact the network or a real provider.

Run at the phase boundary:

```text
python -m unittest discover -s tests -v
bash -n bootstrap/install.sh
pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('bootstrap/install.ps1',[ref]$null,[ref]$null) | Out-Null"
```

Expected: all tests pass, Bash parsing exits `0`, and PowerShell parsing exits `0` on a machine with PowerShell 7.

## Phase 3: Rewrite the stale PRD

**File:** `PRD.md`

The current PRD describes OpenConcierge as if it owns gateways, provider interfaces, databases, and web delivery. Replace those sections with the approved Hermes-native boundary after Phases 1 and 2 pass.

- [ ] **Step 1: Preserve the product intent**

Keep the product name, shopping-concierge purpose, target end users, self-hosting intent, source-backed recommendations, and general physical-product scope.

Change the one-liner to state that OpenConcierge is an open-source Hermes Agent profile distribution and skill, not an independent gateway or agent runtime.

- [ ] **Step 2: Replace the architecture section**

Replace the existing architecture and component table with this model:

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

The component table must assign Hermes ownership to interfaces, models, search backends, MCP, memory, profiles, sessions, and gateways. It must assign OpenConcierge ownership only to shopping behavior, evidence rules, ranking, recommendation format, and the bootstrapper.

- [ ] **Step 3: Replace provider requirements**

Remove `LLMProvider`, `SearchProvider`, and `ProductProvider` interfaces. Replace them with one requirement:

```text
OpenConcierge must use any search capability already visible to the active Hermes profile. It must prefer Hermes web_search, use web_extract when available, discover compatible MCP/plugin tools through Hermes tool discovery when necessary, and never require or configure a named provider.
```

List Exa, Tavily, Brave, DuckDuckGo, SerpAPI, Serper, SearXNG, Firecrawl, Parallel, xAI, and custom tools as examples of integrations Hermes may already expose, not as OpenConcierge dependencies.

- [ ] **Step 4: Replace the data model**

Delete the persistent `User`, `UserProfile`, `ShoppingTask`, `ProductCandidate`, and `Recommendation` database tables. Define the shopping brief and candidate evidence as in-conversation working structures. State that stable preferences use Hermes memory only, require confirmation, and support show/correct/forget controls.

- [ ] **Step 5: Replace functional requirements**

The revised requirements must cover:

1. Guided setup for users with or without Hermes on Windows, macOS, and Linux.
2. Dedicated-profile installation through a Hermes distribution.
3. Existing-profile installation through the OpenConcierge skill without identity/configuration changes.
4. Unlimited but decision-relevant clarification questions with a sufficient-brief stop rule.
5. Provider-neutral search capability resolution.
6. Source-backed candidate evidence and deterministic hard filtering/ranking.
7. Recommendation trade-offs, uncertainty, and observed dates.
8. Explicit-confirmation preference memory and namespaced deletion.
9. Passive installation validation with no billable smoke test.
10. Clear failure behavior instead of fabricated results.

- [ ] **Step 6: Replace non-functional requirements**

Keep self-hostability and privacy, but express them in Hermes terms:

- no OpenConcierge-managed cloud service is required;
- credentials remain in Hermes;
- bootstrap downloads only official Hermes installers and the published OpenConcierge source;
- no secrets appear in logs or distribution content;
- ranking and installer state are testable without live provider calls.

Remove OpenConcierge-owned latency, API cost, database, Docker Compose, and channel-adapter requirements. Hermes controls those concerns.

- [ ] **Step 7: Replace milestones**

Use this implementation sequence:

```text
M1: Core profile distribution, shopping skill, and deterministic ranking
M2: Existing-profile skill installation and preference controls
M3: Cross-platform guided bootstrapper and official Hermes handoff
M4: Clean-machine validation and release hardening
```

Move product APIs, MCP product providers, category packs, WhatsApp onboarding, vector memory, affiliate links, checkout, and web chat to a deferred-expansion section gated by measured failures of the native design.

- [ ] **Step 8: Run a textual consistency review**

Search `PRD.md` for stale ownership terms:

```text
LLMProvider
SearchProvider
ProductProvider
SQLite
Postgres
vector DB
Docker Compose
web chat
custom gateway
checkout
```

Each occurrence must either be removed from v1 requirements or explicitly labeled deferred. Search for provider names and ensure they appear only as examples of reused Hermes integrations, never as required OpenConcierge dependencies.

## Phase 4: Full acceptance and release preparation

- [ ] **Step 1: Run all local tests and static checks**

Run:

```text
python -m unittest discover -s tests -v
python -m py_compile skills/openconcierge/scripts/rank_candidates.py bootstrap/build-release-manifest.py tests/installer/fake_hermes.py
bash -n bootstrap/install.sh
```

Run the PowerShell parser check on a Windows or PowerShell 7 worker:

```text
pwsh -NoProfile -Command "[System.Management.Automation.Language.Parser]::ParseFile('bootstrap/install.ps1',[ref]$null,[ref]$null) | Out-Null"
```

- [ ] **Step 2: Run native Hermes integration checks in an isolated home**

With Hermes installed, set a temporary `HERMES_HOME` and verify:

```text
hermes profile install . --name openconcierge-test --alias --yes
hermes profile show openconcierge-test
hermes -p openconcierge-test skills list --source all --enabled-only
hermes -p openconcierge-test tools list --platform cli
hermes profile update openconcierge-test --yes
```

Expected: the profile and skill are registered, updates preserve user-owned files, and no prompt, search, gateway, or real credential is used.

- [ ] **Step 3: Inspect the release contents**

Run:

```text
python -c "from pathlib import Path; print('\\n'.join(sorted(str(p) for p in Path('.').rglob('*') if p.is_file() and '__pycache__' not in p.parts)))"
```

Confirm the release contains the distribution, skill, bootstrap scripts, tests, and approved PRD/spec/plan files only. Remove generated caches, temporary manifests, fake state, and local credentials.

- [ ] **Step 4: Publish only after source hosting is configured**

Generate release metadata using the actual public distribution and skill sources:

```text
python bootstrap/build-release-manifest.py --distribution-source "$OPENCONCIERGE_PUBLIC_SOURCE" --skill-source openconcierge --version 0.1.0 --output bootstrap/release.json
```

The release operator must replace `$OPENCONCIERGE_PUBLIC_SOURCE` with the verified public distribution URL selected for this project. Do not commit a manifest containing a local path, test URL, credential, or unverified host.

- [ ] **Step 5: Validate the nontechnical user path**

On one clean machine per operating system:

1. Start without Hermes.
2. Run the published bootstrap entry point.
3. Complete official Hermes onboarding.
4. Choose dedicated profile mode.
5. Confirm the profile appears in Hermes Desktop.
6. Confirm no installation prompt or web search was sent automatically.
7. Repeat with an existing Hermes profile and existing-profile mode.
8. Confirm the original profile identity and channel remain unchanged.

Record only pass/fail and error category; do not record model responses, API keys, bot tokens, or user conversations.

## Master definition of done

- The approved design is implemented without a standalone Hermes replacement.
- A general-product shopping workflow works through a Hermes profile or skill.
- Any compatible search integration already exposed by Hermes can be reused without provider-specific OpenConcierge code.
- Dedicated and existing-profile installation modes are both safe and tested.
- Windows, macOS, and Linux have equivalent guided setup paths.
- The PRD describes the actual ownership boundary.
- All available tests and static checks pass.
- No credentials, runtime state, or generated caches are part of the release.
