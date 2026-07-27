# PRD: OpenConcierge — AI Shopping Assistant (Hermes Agent Backend)

## 1. Overview

**Product name:** OpenConcierge (working title)
**One-liner:** An open-source, self-hostable, chat-native AI shopping assistant that interviews users about what they want to buy, researches the market, and recommends the best product for their needs and budget — available on every major messaging platform, powered by any LLM/search stack the operator chooses.

**Inspiration:** Zamana, a personal shopping assistant currently offered on iMessage, which chats with users, asks clarifying questions, and does deep research to find the right product at the right price.

**Core differentiator of this OSS version:** Full provider independence (bring-your-own LLM, bring-your-own search) and multi-platform delivery via **Hermes Agent** as the underlying agent/gateway framework, instead of a single closed iMessage-only product.

## 2. Goals

- Let anyone message the assistant on their platform of choice (Telegram, WhatsApp, Discord, Slack, Signal, WeCom/Lark) and get the same shopping-expert experience.
- Elicit real user needs through conversation instead of requiring structured search forms.
- Perform deep research (web + product search) to shortlist and rank products against the user's stated needs and budget.
- Remember user preferences across sessions to improve future recommendations.
- Allow operators to plug in any LLM provider (OpenAI, Anthropic, OpenRouter, local models via Ollama/vLLM) and any search/product provider.
- Ship as an open-source, self-hostable project with clear extension points for community contributions.

## 3. Non-Goals

- Building a proprietary marketplace or handling payments/checkout in v1.
- Guaranteeing price-matching or purchasing on the user's behalf in v1 (assistant recommends and links out; it does not transact).
- Building custom LLM training/fine-tuning pipelines.
- Supporting every possible chat platform on day one — start with the highest-leverage set and expand via Hermes's existing gateway support.

## 4. Target Users

- **End users:** People who want expert-level shopping research without doing it themselves — e.g., finding the right pillow, laptop, mattress, or gift.
- **Self-hosters / operators:** Developers or small teams who want to run their own instance of the assistant, connected to their preferred AI/search stack, for personal use, a community, or a niche shopping vertical.
- **Contributors:** Open-source developers who want to add new provider integrations (LLMs, search APIs, marketplaces) or new messaging channels.

## 5. Core User Story

> "I'm trying to find a new pillow because the one I'm using hurts my neck, I'm not getting sleepy easily with it, and it's always hot."

The assistant should:
1. Parse this into a structured need (category: pillow; problems: neck pain, poor cooling, sleep onset difficulty).
2. Ask 1–3 targeted follow-up questions (sleep position, budget, region/delivery preference, known allergies).
3. Research pillow types that solve neck pain + heat retention (e.g., cooling gel, contoured memory foam, breathable covers).
4. Search live product listings matching those criteria and the user's budget.
5. Rank and present 2–4 options with a short rationale and trade-offs, plus purchase links.
6. Store the user's preferences (e.g., "prefers cooling materials," "sleeps on side," "budget-conscious") for future tasks.

## 6. System Architecture

### 6.1 Why Hermes Agent

Hermes Agent is chosen as the backend because it already provides:
- A **multi-platform gateway** connecting a single agent process to 7+ chat platforms (Telegram, Discord, Slack, WhatsApp, Signal, Lark, WeCom).
- **Model-agnostic** LLM routing (OpenAI, Anthropic, OpenRouter with 200+ models, and self-hosted backends like Ollama/vLLM/SGLang).
- A **skill system** that persists reusable "skill documents" generated from completed tasks, enabling the agent to improve at recurring task types (e.g., "how to shop for pillows") over time.
- A self-hosted, SQLite-backed session store, avoiding a mandatory managed-cloud dependency.

This means the shopping-assistant-specific work is mostly: (a) defining a shopping "persona" and instruction set, (b) building/integrating research tools, and (c) building the ranking/explanation logic — not re-implementing chat gateways or LLM routing.

### 6.2 High-Level Diagram (textual)

```
[Telegram] [WhatsApp] [Discord] [Slack] [Signal] [Web Chat]
        \      |         |        |        |      /
         \_____|_________|________|________|_____/
                        |
                Hermes Agent Gateway
                        |
              OpenConcierge Shopping Agent (skills + persona)
                        |
        -----------------------------------------
        |               |                       |
   LLM Provider    Search/Product Tools     Memory Store
 (pluggable via    (pluggable via MCP/      (SQLite / Postgres
  Hermes config)    tool interface)          + optional vector DB)
```

### 6.3 Components

| Component | Responsibility | Notes |
|---|---|---|
| Hermes Agent Gateway | Normalizes messages across chat platforms into a single agent loop | Existing Hermes functionality, configured not rebuilt |
| OpenConcierge Persona/Instructions | Defines tone, goals, question style, safety rules | Markdown/config files loaded into Hermes agent context |
| Requirement Extraction Skill | Converts free text into a structured `ShoppingTask` | Implemented as a Hermes skill using LLM function-calling |
| Follow-up Question Skill | Decides what's missing and asks targeted questions | Category-specific question templates + LLM fallback |
| Research & Search Tools | Calls external search/product APIs | Implemented as MCP tools or Hermes-native tools |
| Ranking & Explanation Skill | Filters/scores products, explains trade-offs | Deterministic scoring + LLM-generated explanation |
| Memory Store | Persists user profile, preferences, past tasks | SQLite by default; Postgres/vector DB optional |
| Provider Config Layer | Lets operator choose LLM + search provider | Environment/config-driven, following Hermes's provider model |

## 7. Functional Requirements

### 7.1 Conversation & Requirement Capture
- FR1: The agent must detect shopping intent from free-form natural language across supported platforms.
- FR2: The agent must extract a structured `ShoppingTask` (category, problems, must-haves, nice-to-haves, budget, region, deadline) from the conversation.
- FR3: The agent must ask clarifying questions only for missing high-value fields (avoid over-questioning); category-specific templates should exist for common verticals (pillows, mattresses, laptops, shoes, gifts).
- FR4: The agent must support multi-turn refinement (user can correct/add requirements at any point).

### 7.2 Research & Ranking
- FR5: The agent must call at least one external search/product-data tool to gather live candidate products.
- FR6: The agent must normalize product data into a common schema (title, price, currency, seller, rating, specs, shipping/delivery info, URL).
- FR7: The agent must apply hard filters (budget ceiling, region availability, explicit must-haves) before ranking.
- FR8: The agent must score remaining candidates using a transparent, explainable scoring method (not a black box), combining requirement match, rating, and price.
- FR9: The agent must present a shortlist (2–4 items) with a plain-language rationale per item and visible trade-offs.

### 7.3 Personalization & Memory
- FR10: The agent must persist user preferences derived from conversations and choices (e.g., preferred brands, sizing, allergies, budget sensitivity).
- FR11: The agent must reuse stored preferences in future shopping tasks without re-asking already-known information, unless the user indicates a change.
- FR12: Users must be able to view and delete their stored profile/preference data (privacy requirement).

### 7.4 Multi-Platform Delivery
- FR13: The same agent logic must be accessible from at least Telegram and WhatsApp at v1 launch, using Hermes's existing channel adapters.
- FR14: Message formatting (links, lists, buttons where supported) must degrade gracefully on platforms with limited rich-message support.
- FR15: A web chat interface should be available for platforms/testing where no messaging account is required.

### 7.5 Extensibility (Bring-Your-Own AI/Search)
- FR16: The system must allow operators to configure their LLM provider (e.g., OpenAI, Anthropic, OpenRouter, local Ollama/vLLM) via configuration, without code changes, using Hermes's existing model-routing support.
- FR17: The system must expose a documented tool/plugin interface (ideally MCP-based) so contributors can add new search or product-data providers without modifying core agent logic.
- FR18: Default reference implementations should be provided for at least one hosted LLM provider and one hosted search/product provider, to ensure the project works out-of-the-box.

## 8. Non-Functional Requirements

- **NFR1 (Self-hostable):** The full stack must run via a single docker-compose (or equivalent) setup for local/self-hosted deployment.
- **NFR2 (Latency):** Initial acknowledgment/response to a user message should occur within ~3 seconds even if deep research runs asynchronously with a "still researching" follow-up message.
- **NFR3 (Cost transparency):** Operators should be able to see estimated LLM/search API cost per shopping task (token/call counters), given usage-based pricing of most providers.
- **NFR4 (Privacy):** No user data should be sent to third-party providers beyond what's required for the active LLM/search call; profile data must be stored locally by default (no mandatory external telemetry).
- **NFR5 (Reliability):** If a configured LLM or search provider fails, the system should surface a clear error to the user rather than hallucinate results.
- **NFR6 (Testability):** Core requirement-extraction, filtering, and ranking logic must be unit-testable independent of any live LLM or search call (via mocked providers).

## 9. Data Model (Initial Draft)

```yaml
User:
  id: string
  platform_ids: { telegram: string?, whatsapp: string?, ... }
  created_at: datetime

UserProfile:
  user_id: string
  preferences: json      # e.g. { "brand_avoid": ["X"], "size": "EU 42", "budget_sensitivity": "high" }
  constraints: json      # e.g. { "region": "UAE", "allergies": ["latex"] }
  updated_at: datetime

ShoppingTask:
  id: string
  user_id: string
  category: string
  problems: string[]
  must_haves: string[]
  nice_to_haves: string[]
  budget: number?
  currency: string?
  region: string?
  status: enum[collecting, researching, ready, closed]
  created_at: datetime

ProductCandidate:
  id: string
  task_id: string
  title: string
  price: number
  currency: string
  seller: string
  rating: number?
  specs: json
  url: string
  score: number
  score_breakdown: json

Recommendation:
  id: string
  task_id: string
  product_candidate_ids: string[]
  explanation: string
  presented_at: datetime
```

## 10. Provider Interfaces (Pluggability Contract)

```ts
interface LLMProvider {
  name: string;
  chat(messages: ChatMessage[], options?: ChatOptions): Promise<ChatMessage>;
  callTool<T>(schema: JSONSchema, messages: ChatMessage[]): Promise<T>;
}

interface SearchProvider {
  search(query: string, options?: SearchOptions): Promise<SearchResult[]>;
}

interface ProductProvider {
  searchProducts(query: ProductSearchQuery): Promise<Product[]>;
  getProductDetails(id: string): Promise<Product>;
}
```

Operators configure which concrete implementation of each interface to use via a config file / environment variables consumed by the Hermes agent runtime. New providers are added by implementing the interface and registering it — no core agent code changes required.

## 11. Milestones / Roadmap

### M1 — Core Agent MVP (single channel)
- Hermes Agent configured with OpenConcierge persona and one LLM provider.
- Requirement extraction + basic follow-up questions for 2–3 categories.
- One search/product provider integrated.
- Deployed on Telegram only.

### M2 — Ranking & Explanation
- Structured scoring engine (hard filters + weighted soft scoring).
- LLM-generated shortlist explanations with trade-offs.
- Basic user profile persistence (SQLite).

### M3 — Multi-Platform Expansion
- Add WhatsApp and web chat via existing Hermes channel adapters.
- Graceful formatting fallback for limited-rich-message platforms.

### M4 — Pluggability & Docs
- Finalize LLMProvider/SearchProvider/ProductProvider interfaces.
- Reference implementations for at least 2 LLM providers and 2 search/product providers.
- Contributor docs: "Add a new provider," "Add a new channel," "Add a new shopping category."

### M5 — Personalization Depth
- Long-term preference memory reused across tasks.
- Privacy controls: view/delete profile data.
- Optional vector-based memory for richer personalization.

## 12. Open Questions

- Which default hosted search/product API should ship as the reference implementation (general web search vs. a specific marketplace API)?
- Should checkout/purchase links be affiliate-tagged by default, and how should that be disclosed to keep the OSS project's incentives transparent?
- How should the project handle regions/marketplaces with no public product-search API (e.g., scraping vs. official partnerships)?
- Should category-specific question templates be community-contributed (a "category pack" system), and if so, what's the contribution format?

## 13. Success Metrics (v1)

- Time from first message to first product shortlist (target: under 3 minutes of active conversation).
- % of shopping tasks completed without the user abandoning the conversation.
- Number of follow-up questions asked per task (should trend down as personalization improves).
- Number of community-contributed providers/channels within 3 months of open-sourcing.
