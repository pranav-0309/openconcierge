# Research and Evidence

This document expands the `## Search Capability Resolution` and `## Candidate Evidence` sections of `SKILL.md`.

## Search capability non-contract

The skill does not require `web_search`, a named provider, a particular MCP server, or a provider API key in its metadata. Search capability is selected at runtime from the active Hermes profile.

## Resolution order

1. Use Hermes canonical `web_search` first when it is available; Hermes selects the configured backend through its own `web.search_backend`/`web.backend` settings.
2. Use `web_extract` for direct-page verification when available.
3. If canonical search is absent or insufficient, call `tool_search` with a capability query such as `web search product search marketplace search`, then call `tool_describe` and `tool_call` for a compatible MCP/plugin tool.
4. Accept any discoverable tool that takes a query and returns inspectable result URLs; do not match only on brand names.
5. Use an installed fallback search skill when Hermes makes one available.
6. Prefer the canonical backend and use one configured fallback after failure; do not fan out across all providers.
7. Never ask for Exa, Tavily, SerpAPI, Serper, Brave, DuckDuckGo, or another key when Hermes already exposes the integration.

## Evidence rules

- Verify each candidate against a direct product or manufacturer page when possible.
- Record the observation date for price, availability, specifications, and material claims.
- Use multiple independent sources when a recommendation relies on disputed, subjective, health-related, durability, or performance claims.
- Mark inaccessible, stale, conflicting, or absent facts as `unknown`. Never present an unknown `must` as satisfied.
- Do not treat older observations as current. If a page is older than the brief's freshness expectation, downgrade or replace it.

## Candidate evidence structure

Produce this normalized structure for each shortlisted candidate before passing it to `scripts/rank_candidates.py`:

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

Field rules:

- `name` and `product_url` are required. `product_url` must be a usable `http` or `https` URL.
- `importance` is exactly `must`, `core`, `preference`, or `nice`. The first three participate in scoring; `must` is enforced as a hard constraint.
- `match` is exactly `strong`, `partial`, `none`, or `unknown`.
- `strong` or `partial` requires at least one usable `http` or `https` URL in `source_urls`; the ranking helper downgrades unsupported positive matches to `unknown`.
- `observed_price` may be `null` when the price is unknown; `ships_to_region` may be `true`, `false`, or `unknown`.
- `tradeoffs` is a list of short, plain-language notes about limitations, conflicts, or follow-ups.