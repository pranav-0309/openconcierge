# OpenConcierge Hermes-Native Add-on Design

**Status:** Approved
**Date:** 2026-07-27

## 1. Decision

OpenConcierge will be built as a native Hermes Agent add-on, not as a standalone agent platform.

The primary artifact is a Hermes **profile distribution** containing an OpenConcierge personality and shopping skill. The same shopping skill is also installable into an existing Hermes profile for users who want to keep their current agent identity and messaging channels.

Hermes remains responsible for:

- Desktop, CLI, TUI, and messaging interfaces
- LLM provider configuration and model routing
- Web search and other tools
- Profiles, sessions, memory, and state
- Gateway processes and channel adapters
- Skill discovery, installation, and updates
- Provider credentials and secret storage

OpenConcierge is responsible for:

- Shopping-specific interviewing behavior
- Research and evidence rules
- Candidate filtering and explainable ranking
- Recommendation presentation
- Shopping-preference memory rules
- A guided installation experience

OpenConcierge will not fork, embed, proxy, or recreate the Hermes runtime.

## 2. Product Goal

A person should be able to add a trustworthy shopping concierge to Hermes without editing code, YAML, or environment files.

The supported outcomes are:

1. A user without Hermes installs the official Hermes Desktop application through a guided flow, completes Hermes onboarding, and then installs OpenConcierge.
2. A user with Hermes installs OpenConcierge directly.
3. The user chooses between a dedicated OpenConcierge profile and an OpenConcierge skill inside an existing profile.
4. The result is immediately visible in Hermes Desktop and works through Hermes's existing interfaces.

## 3. MVP Success Criteria

The MVP is complete when:

- Windows, macOS, and Linux users have a guided setup path.
- A configured Hermes user can install OpenConcierge without manually editing files.
- A user without Hermes is handed off to the official Hermes installation experience and can resume OpenConcierge setup afterward.
- Dedicated-profile installation creates an isolated OpenConcierge personality and memory space.
- Existing-profile installation does not replace the user's personality, provider configuration, memory, or gateway configuration.
- OpenConcierge can research general physical products using any compatible search capability already enabled in the selected Hermes profile.
- OpenConcierge does not require a specific search provider, replace the user's chosen backend, or request credentials for an integration Hermes can already use.
- Recommendations respect confirmed hard constraints and include source-backed trade-offs.
- Installation performs no model prompt, web search, or other billable smoke test.
- Installation and updates do not expose, transmit, or log credentials.

## 4. Explicit Non-Goals

The MVP will not include:

- A separate OpenConcierge desktop application
- A standalone backend or agent loop
- Custom chat gateways or channel adapters
- A web chat implementation
- An OpenConcierge LLM-provider abstraction
- A product-provider abstraction
- A hosted product-search API integration
- An MCP server or background sidecar
- A custom database, vector database, or memory service
- Product scraping infrastructure
- Checkout, payment, or purchasing
- Affiliate links
- Category-specific packs
- WhatsApp onboarding
- Asynchronous research workers
- Token-cost dashboards
- Custom telemetry
- A fixed maximum number of clarifying questions

These items may be reconsidered only after usage evidence shows that Hermes-native capabilities cannot deliver the core shopping experience.

## 5. Architecture

### 5.1 Distribution artifact

The public OpenConcierge repository is the Hermes profile distribution source.

```text
openconcierge/
├── distribution.yaml
├── SOUL.md
├── skills/
│   └── openconcierge/
│       ├── SKILL.md
│       ├── references/
│       │   ├── interviewing.md
│       │   ├── research-and-evidence.md
│       │   ├── recommendations.md
│       │   └── memory-and-privacy.md
│       └── scripts/
│           └── rank_candidates.py
├── bootstrap/
│   ├── install.ps1
│   └── install.sh
└── tests/
    ├── fixtures/
    ├── installer/
    ├── ranking/
    └── skill/
```

Only the following files belong to the installed Hermes distribution:

- `distribution.yaml`
- `SOUL.md`
- `skills/openconcierge/`

Bootstrap code and repository tests are development and release assets, not runtime components of the Hermes profile.

### 5.2 Distribution manifest

The first distribution uses these semantics:

```yaml
name: openconcierge
version: 0.1.0
description: A source-backed personal shopping concierge for Hermes Agent
hermes_requires: ">=0.12.0"
distribution_owned:
  - distribution.yaml
  - SOUL.md
  - skills/openconcierge/
```

The distribution declares no OpenConcierge-specific environment variables. Model and web-tool credentials remain Hermes concerns.

The narrow `distribution_owned` list ensures OpenConcierge updates can replace its own personality and skill while preserving user credentials, sessions, memories, local settings, and additional skills.

### 5.3 Personality

`SOUL.md` applies only in dedicated-profile mode. It establishes that the agent:

- Acts as a patient, evidence-oriented personal shopping concierge
- Learns the user's actual intent before researching
- Asks only questions that could materially affect the recommendation
- Never invents products, prices, reviews, availability, or specifications
- Separates verified facts from inferences
- Explains uncertainty and trade-offs plainly
- Does not pressure users to purchase
- Does not transact or claim to reserve inventory
- Uses concise language appropriate to the active messaging surface

Existing-profile mode installs only the skill and never modifies the profile's `SOUL.md`.

### 5.4 Shopping skill

`skills/openconcierge/SKILL.md` is the single entry point for shopping tasks. It supports explicit `/openconcierge` invocation and natural shopping requests when Hermes selects the skill.

The skill references focused documents rather than placing the entire workflow in one large prompt. It calls its bundled dependency-free ranking script through Hermes's existing execution tools after candidate evidence has been normalized. It does not start or depend on a persistent process.

### 5.5 Search capability resolution

OpenConcierge is search-provider neutral. Its skill metadata must not require a provider-specific tool, API key, or MCP server, and it must not require the canonical `web_search` tool as a condition for the skill to load.

For every research task, the skill resolves search capabilities in this order:

1. Use Hermes's canonical `web_search` capability when available. Hermes, not OpenConcierge, selects the configured backend. This automatically respects a user's existing Hermes backend such as Exa, Tavily, Brave, DuckDuckGo, SearXNG, Firecrawl, Parallel, xAI, or another backend supported by their Hermes version.
2. Use `web_extract` when available for product-page verification. A search-only backend remains valid; lack of extraction must not hide or disable OpenConcierge.
3. If the canonical capability is absent or cannot satisfy the task, use Hermes's progressive tool discovery to find enabled MCP or plugin tools whose descriptions and schemas provide web, product, marketplace, or general search. This covers integrations such as SerpAPI, Serper, custom Exa or Tavily MCP servers, and future providers without adding OpenConcierge adapters.
4. If Hermes surfaces an installed fallback search skill, use that skill's documented procedure instead of asking the user to install a duplicate provider.
5. If several compatible capabilities exist, prefer the user's canonical Hermes backend. Use another configured capability only for a missing feature or after a failure; do not fan out across every provider by default.

A compatible custom integration must be visible to Hermes and expose a discoverable search operation that accepts a query and returns result URLs with enough evidence to inspect. Provider brand names are examples, not a hardcoded allowlist.

OpenConcierge never changes the selected Hermes backend, duplicates provider configuration, or asks for an API key that Hermes has already configured.

## 6. Installation Design

### 6.1 Entry points

OpenConcierge provides two setup entry points backed by the same behavior:

- A PowerShell command for Windows
- A POSIX shell command for macOS and Linux

Hermes Desktop remains the everyday graphical interface after setup. OpenConcierge does not ship a second chat application.

### 6.2 Installer principles

The bootstrapper must:

- Delegate Hermes installation to official Hermes installers
- Never modify Hermes source files
- Use supported Hermes CLI commands for profiles and skills
- Be resumable after the official Hermes setup flow
- Be idempotent
- Explain every choice in non-technical language
- Avoid showing or requesting secrets itself
- Open Hermes Desktop settings when provider or gateway credentials are needed
- End with passive validation only

### 6.3 Hermes detection

The bootstrapper checks:

1. Whether the `hermes` command is available.
2. Whether `hermes doctor` can inspect the installation.
3. Whether the installed Hermes version satisfies the distribution requirement.
4. Whether at least one profile has a usable model configuration.
5. Whether Hermes Desktop can be launched.

A failed check produces a plain-language next action. It never attempts a live agent conversation.

### 6.4 When Hermes is missing

The setup flow is guided rather than silent.

- On Windows and macOS, the bootstrapper launches the current official Hermes Desktop installer and asks the user to complete its normal onboarding.
- On Linux, the bootstrapper uses the official Hermes installation path and launches Hermes Desktop through the supported `hermes desktop` command.
- The bootstrapper waits for completion or lets the user explicitly continue after installation.
- Hermes handles provider sign-in and model selection.
- OpenConcierge setup resumes only after Hermes is available.

OpenConcierge does not mirror or redistribute Hermes binaries. Release code must obtain Hermes only from an official Nous Research source and must preserve operating-system signature or checksum verification when the official distribution supplies it.

### 6.5 Installation mode choice

After Hermes is ready, the installer asks:

#### Option A: Dedicated OpenConcierge

Use this when the user wants a separate shopping agent.

Behavior:

1. Ask which configured Hermes profile should supply reusable model settings.
2. Use supported Hermes profile clone/install commands so reusable configuration is inherited where Hermes permits it.
3. Install the OpenConcierge profile distribution under the name `openconcierge`.
4. Replace the cloned personality with OpenConcierge's `SOUL.md`.
5. Install the OpenConcierge skill.
6. Preserve credentials and model settings that Hermes safely carries across profiles.
7. If an OAuth account or provider cannot be reused, open the OpenConcierge profile's provider settings in Hermes Desktop.
8. Make the new profile visible in Hermes Desktop without changing the user's active default profile unless the user asks.

Dedicated mode gets isolated Hermes sessions and memory.

Hermes profiles cannot run the same active bot token concurrently. The installer therefore offers:

- Use OpenConcierge in Hermes Desktop with no messaging setup, or
- Create a separate Telegram bot for OpenConcierge through Hermes's official gateway setup

The installer must not copy an active gateway token from another profile.

#### Option B: Add shopping to my current agent

Use this when the user wants OpenConcierge on an existing bot identity or channel.

Behavior:

1. Ask which Hermes profile should receive the skill.
2. Install the same `openconcierge` skill into that profile through Hermes's supported skill installer.
3. Do not change `SOUL.md`, model configuration, provider credentials, memory configuration, or gateway settings.
4. Keep the profile's existing messaging identity and channels.
5. Namespace any remembered shopping preferences so they remain distinguishable from other profile memory.

The canonical skill directory is published through Hermes's supported skill distribution mechanism so the profile distribution and standalone skill cannot drift apart.

### 6.6 Passive completion checks

Installation ends after confirming only that:

- Hermes reports a healthy local installation.
- The selected profile exists.
- The OpenConcierge distribution or skill is registered.
- The profile exposes either Hermes's canonical web search, a compatible MCP/plugin search tool, or an installed fallback search skill; otherwise Hermes Desktop clearly shows that search setup is still required.
- No profile or gateway token conflict was introduced.

The installer does not send a shopping request, invoke a model, search the web, or incur provider cost.

### 6.7 Updates and removal

Native Hermes lifecycle commands remain the source of truth:

- Dedicated mode updates through Hermes profile-distribution updates.
- Existing-profile mode updates through Hermes skill updates.
- Dedicated mode is removed by deleting the OpenConcierge profile.
- Existing-profile mode is removed by uninstalling the OpenConcierge skill.

OpenConcierge does not build a parallel updater or uninstaller.

## 7. Shopping Conversation Design

### 7.1 Intent capture

The agent maintains an in-conversation shopping brief with these fields:

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

This structure is working context, not a new persisted database model.

### 7.2 Clarifying-question rule

There is no numerical question limit.

The agent asks a clarifying question only when the answer could:

- Change which products qualify
- Change the ranking materially
- Establish budget, currency, or regional availability
- Resolve contradictory requirements
- Prevent an unsuitable or unsafe recommendation
- Distinguish between meaningfully different product types

The agent must not:

- Ask for information already provided or remembered
- Ask generic questionnaire items unrelated to the current purchase
- Continue questioning after it has enough information to perform a useful search
- Block research on a low-value preference
- Treat optional information as mandatory

The user may say "use your judgment," skip a question, or revise any answer. The agent then proceeds with explicit assumptions and labels them.

### 7.3 Research workflow

Once intent is sufficiently clear, the agent:

1. Summarizes the brief and resolves any remaining contradiction.
2. Resolves and uses the selected profile's existing search capability according to Section 5.5.
3. Builds a candidate set from accessible sources.
4. Verifies each shortlisted candidate against a direct product or manufacturer page when possible.
5. Records the source and observation date for price, availability, specifications, and material claims.
6. Rejects candidates that fail verified hard constraints.
7. Marks unknown facts as unknown rather than treating them as matches.
8. Ranks the remaining candidates using the transparent method below.
9. Presents 2–4 options when enough qualified products exist.

The agent should use multiple independent sources when a recommendation relies on disputed, subjective, health-related, durability, or performance claims.

### 7.4 Candidate evidence structure

The skill passes normalized evidence to the ranking helper:

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

A positive match must include source evidence. Unsupported positive matches are downgraded to `unknown` before scoring.

### 7.5 Filtering and ranking

`scripts/rank_candidates.py` uses only the Python standard library.

Hard filters remove a candidate when verified evidence shows that it violates:

- A maximum budget
- Regional availability
- An explicit exclusion
- A required compatibility condition
- A must-have feature
- A delivery deadline

An unverified must-have cannot be presented as satisfied or enter the ranked shortlist. It may be shown separately as an unranked lead that requires user verification.

Soft criteria use these deterministic values:

- `strong`: 1.0
- `partial`: 0.5
- `none`: 0.0
- `unknown`: 0.0

Criterion weights are:

- `core`: 3
- `preference`: 2
- `nice`: 1

The fit score is the weighted earned value divided by the weighted possible value. The script returns the score and criterion-level breakdown. It does not invent criterion judgments; those must come from source-backed candidate evidence.

Price is shown directly and participates as a hard filter when the user sets a maximum. The agent explains value qualitatively rather than adding a universal price weight that would distort categories with very different price distributions.

### 7.6 Recommendation output

A completed recommendation contains:

1. A short statement of the understood need.
2. Any assumptions the user skipped or left unknown.
3. Two to four qualified options, when available.
4. For each option:
   - Current observed price and currency
   - Seller or manufacturer
   - Why it fits
   - Important trade-offs
   - Unverified details
   - Direct source links
5. A concise comparison explaining why the top option ranks first.
6. The date on which prices and availability were observed.
7. A reminder to verify volatile price and stock information before purchase.

The agent must not manufacture a full shortlist when fewer than two products meet the evidence threshold. It should present the qualified result and explain what prevented additional matches.

## 8. Memory and Privacy

OpenConcierge uses Hermes memory only.

### 8.1 What may be remembered

Stable shopping preferences are remembered only after the user confirms them, including:

- Preferred or avoided brands
- Common sizing
- Budget sensitivity
- Preferred materials or product characteristics
- Region and currency
- Recurring compatibility constraints

Transient task details, unconfirmed inferences, and browsing history are not promoted to long-term preferences.

Health information, allergies, disability-related needs, and other sensitive constraints are used for the current task but are not stored as durable preferences unless the user explicitly asks for that behavior.

### 8.2 User controls

The skill supports these requests in natural language or as arguments to `/openconcierge`:

- Show my shopping preferences
- Correct a shopping preference
- Forget one shopping preference
- Forget all shopping preferences

In dedicated mode, deleting the Hermes profile removes its isolated OpenConcierge memory and sessions through Hermes's native lifecycle. In existing-profile mode, the skill removes only namespaced shopping-preference entries and does not delete unrelated memory.

## 9. Failure Handling

### 9.1 Research failures

- If no compatible search capability is available after canonical and deferred-tool discovery, OpenConcierge explains that live recommendations require an enabled Hermes search integration and directs the user to Hermes Desktop's tools, skills, or MCP settings without prescribing a provider.
- If the selected search capability fails, OpenConcierge may try one other already-configured compatible capability. If none succeeds, it reports the failure and does not substitute fabricated results.
- If prices or availability cannot be verified, it labels them unknown.
- If no products satisfy hard constraints, it explains which constraints eliminated candidates and asks whether the user wants to relax one.
- If sources disagree, it describes the disagreement and lowers confidence.
- If a product page is stale or inaccessible, it is not treated as current evidence.

### 9.2 Installation failures

- An unsupported Hermes version stops before modifying profiles.
- Cancellation leaves existing Hermes profiles unchanged.
- Re-running setup detects prior installation and offers update, repair, mode change, or cancel.
- A name collision never overwrites an unrelated profile without explicit confirmation.
- Gateway token conflicts are surfaced before a new gateway starts.
- Installer logs redact paths or values that could reveal credentials.

## 10. Testing Strategy

### 10.1 Distribution tests

Validate that:

- `distribution.yaml` parses and contains the intended ownership boundary.
- The minimum Hermes version is enforced.
- `SOUL.md` and every skill reference are present.
- The standalone skill and profile-bundled skill are byte-identical at release time.
- Distribution content contains no credentials, sessions, memory, or generated state.
- Skill metadata contains no provider-specific search requirement and does not hide the skill when canonical `web_search` is absent.

### 10.2 Ranking tests

Unit-test:

- Every hard-filter condition
- Unknown versus failed criteria
- Weighted scoring and tie behavior
- Missing prices and currencies
- Unsupported positive evidence
- Deterministic output for fixed input

### 10.3 Skill behavior fixtures

Use recorded, provider-independent fixtures for scenarios such as:

- A cooling pillow for neck discomfort
- A laptop constrained by software compatibility and budget
- A gift with uncertain recipient preferences
- A product unavailable in the user's region
- Contradictory requirements
- A user who skips questions
- A user who changes requirements mid-search
- A search with only one qualified candidate
- A request containing sensitive health information
- A canonical Hermes web-search backend
- A search-only backend with no extraction capability
- A custom MCP search tool with a nonstandard tool name
- Multiple configured search capabilities, verifying canonical-backend preference
- Canonical search failure with one configured fallback
- No compatible search capability

Assertions focus on observable behavior:

- Questions are relevant rather than numerically capped.
- Known information is not requested again.
- Hard constraints are not violated.
- Unsupported facts are labeled unknown.
- Recommendations include evidence and trade-offs.
- Sensitive information is not automatically persisted.
- Existing compatible search capabilities are reused without provider-specific setup.
- Deferred MCP/plugin search tools are discovered by capability rather than by hardcoded name.
- Multiple providers are not queried unnecessarily.

### 10.4 Installer tests

Test Windows, macOS, and Linux flows with mocked process and filesystem boundaries:

- Hermes present and healthy
- Hermes missing
- Official installer cancellation
- Unsupported Hermes version
- Dedicated-profile installation
- Existing-profile skill installation
- Reusable provider configuration
- Provider re-authentication required
- Existing OpenConcierge installation
- Profile-name collision
- Gateway token collision
- Interrupted and resumed installation
- Idempotent re-run
- Passive completion with no model or web calls

### 10.5 Native integration tests

Use a temporary `HERMES_HOME` to verify native Hermes commands install, discover, update, and remove the distribution and skill. These tests validate registration and file ownership only; installation never performs a live shopping conversation.

## 11. Delivery Sequence

### Phase 1: Native distribution

- Create and manually install the OpenConcierge profile distribution.
- Author and dogfood `SOUL.md` and the shopping skill.
- Implement and unit-test deterministic filtering and ranking.
- Verify update and removal semantics with a temporary Hermes home.

### Phase 2: Existing-profile mode

- Publish the same skill through Hermes's supported skill distribution path.
- Confirm installation leaves personality, provider, memory, and gateways unchanged.
- Add namespaced shopping-preference controls.

### Phase 3: Guided bootstrapper

- Implement the existing-Hermes path first.
- Add dedicated-versus-existing mode selection.
- Add passive validation and repair behavior.
- Add official Hermes Desktop handoff for missing-Hermes users on Windows, macOS, and Linux.

### Phase 4: Release hardening

- Run clean-machine installation tests on all three operating systems.
- Verify no secret leakage in package contents or logs.
- Add plain-language install, update, remove, and Telegram guidance.
- Publish a tagged OpenConcierge distribution release.

## 12. PRD Changes Required

The current PRD should be rewritten to reflect this ownership boundary.

Remove OpenConcierge-owned versions of:

- The Hermes gateway
- LLM routing and `LLMProvider`
- `SearchProvider` and `ProductProvider`
- SQLite/Postgres/vector memory architecture
- User, task, product, and recommendation database tables
- Docker Compose as an OpenConcierge runtime
- Web chat and multi-channel delivery implementation
- Provider registration and custom channel roadmaps

Replace them with requirements for:

- A Hermes profile distribution
- A standalone Hermes skill installation mode
- A guided official-Hermes bootstrap flow
- Provider-neutral research that reuses canonical, MCP, plugin, or fallback search capabilities already configured in Hermes
- In-conversation structured shopping briefs
- Dependency-free deterministic filtering and ranking
- Hermes-native memory with shopping-preference controls
- Passive installation verification

## 13. Deferred Expansion Gates

A deferred component may enter scope only after a measured failure of the native design:

- Add an MCP product provider only if web research repeatedly fails to provide sufficiently current or structured product evidence.
- Add category packs only if general-product evaluations show recurring category-specific questioning failures.
- Add a custom memory layer only if Hermes memory cannot support accurate view, correction, and deletion of shopping preferences.
- Add WhatsApp-specific onboarding only after the Telegram and Desktop paths are reliable.
- Add affiliate links only after a disclosure policy and user-value case are approved.

The default response to a new capability request is to improve the profile or skill before creating a new service.

## 14. References

- Hermes installation: https://hermes-agent.nousresearch.com/docs/getting-started/installation
- Hermes Desktop: https://hermes-agent.nousresearch.com/docs/user-guide/desktop
- Hermes profiles: https://hermes-agent.nousresearch.com/docs/user-guide/profiles
- Hermes profile distributions: https://hermes-agent.nousresearch.com/docs/user-guide/profile-distributions
- Hermes skills: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
