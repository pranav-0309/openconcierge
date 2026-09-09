# Research and Evidence Rules

How to search, what counts as evidence, and how to treat reviews.
OpenConcierge never configures or requests a specific search provider —
it uses whatever capability the host session already exposes.

## Search resolution order

1. **The host's built-in web search** — honoring whatever backend it is
   configured with. Use it first.
2. **Web page extraction**, when available, to open and verify direct
   product/manufacturer pages.
3. **Any discoverable MCP/plugin search tool** the user has installed.
4. **One fallback** — if a search fails (error, no results, unusable
   results), try at most one already-configured alternative. Never fan
   out across every provider; never retry the same failing provider in a
   loop.

OpenConcierge never asks for a provider API key the host has already
configured, and never duplicates provider configuration.

## Missing search capability

If the host exposes no way to search the web at all:

- **Say so honestly.** "I don't have a way to search the web in this
  session, so I can't research live options."
- **Ask the user to provide a search capability** — enabling a built-in
  web-search tool or connecting an MCP search server.
- **Never ask the user to paste research.** No "just copy in the top
  results from Google".
- **Never fabricate results in place of search.** No invented products,
  prices, or ratings from memory presented as findings.
- **If the user volunteers research unprompted** — links, specs, notes —
  accept it as first-class evidence with full source-tracking. Record
  source URLs, observed dates, and which claims came from the user. Treat
  user-provided material exactly like search results when scoring and
  presenting, and label it as user-provided where it matters.

## Candidate evidence

For every shortlisted candidate, record (per the data model):

- name, direct product URL, seller or manufacturer
- observed price, currency, and **observed date** (when you saw it)
- regional availability: `true` / `false` / `unknown`
- per-criterion match: `strong` / `partial` / `none` / `unknown`, each
  with the source URL(s) supporting it
- trade-offs worth telling the user about

## Verification rules

- **Verify against a direct product or manufacturer page when possible.**
  A retailer listing page or the manufacturer's spec page is the
  authority for price, specs, and availability.
- **Label honestly what you couldn't verify.** Anything inaccessible,
  stale, conflicting between sources, or simply absent is `unknown` —
  never guessed, never rounded up to a match. `unknown` flows through
  scoring as `unknown`; it never becomes `strong`.
- **Price is a snapshot.** Always carry the observed date with any price
  you present. If you saw the price a week ago, say so.
- **Regional availability** must come from a shipping/seller page when
  possible; if the seller doesn't clearly ship to the user's region,
  that's `unknown`, not `true`.
- **Never fabricate** products, prices, availability, ratings, or
  specifications. A gap in evidence is a finding ("unknown"), not an
  invitation to fill it in.

## Review skepticism

Reviews are evidence, but weak evidence. Apply these rules:

- **Ratings from manufacturer or seller pages alone are never
  sufficient.** They are curated, and often filtered. They may support a
  claim made elsewhere; they cannot carry a claim by themselves.
- **Down-weight affiliate-driven "best X" listicles.** Recognizable
  patterns: every product "the best", buy-buttons/affiliate tags to the
  same retailers, near-identical pros/cons phrasing, no stated testing
  methodology. Use them for discovery (finding candidate names), not for
  verification or scoring.
- **Treat suspicious review patterns as low-quality signals:**
  - Thin review counts (a handful of reviews carrying a high rating)
  - Uniformly glowing ratings with no critical mass of detail
  - Templated praise — repeated phrasing across different reviewers
  - Rating spikes uncorrelated with review content
- When review evidence is doubtful, the criterion it supports drops to
  `partial` or `unknown` — say why in the trade-offs.
- Independent testing/review outlets with stated methodology, owner
  forums, and long-tail user reviews with specifics are the stronger
  signals.

## Search hygiene

- Search in the user's region and language where possible.
- Run at least two distinct queries per research pass (e.g. problem-
  phrased "best pillow for neck pain side sleeper" and product-typed
  "cervical memory foam pillow cooling") — different phrasings surface
  different candidates.
- Prefer fresh sources; note the year of any review or roundup you rely
  on, and discount stale ones (last year's model, closed listings).
- Don't over-search. Once you have 5-10 plausible candidates with
  evidence, move to ranking.