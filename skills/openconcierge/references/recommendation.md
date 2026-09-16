# Recommendation — Scoring, Presentation, and Feedback

This document is the complete prose specification of the ranking method.
The script `scripts/rank_candidates.py` implements exactly this method
for hosts that can execute scripts. Script-capable and script-less hosts
must produce the same ranking for the same input — only the mechanism
differs. When the script cannot run, apply these rules by hand, step by
step, and be strict about it.

## Step 1 — Hard filters (before any scoring)

A candidate is **eliminated** (never recommended) if any of the following
holds:

1. **Over budget.** Observed price exceeds the brief's maximum budget.
   (An unknown price does NOT eliminate — it passes the filter and is
   flagged as unverified in presentation.)
2. **Regionally unavailable.** The candidate verifiably does not ship to
   the user's region. Unknown regional availability does NOT eliminate —
   it passes and is flagged.
3. **Explicitly excluded.** The candidate's name or seller matches an
   item on the brief's avoid list or a stated exclusion (brand,
   material, retailer).
4. **Must-have not met.** Any requirement marked `must` has a match of
   `none` or `unknown`. Only `strong` or `partial` satisfies a must.
   (This is why must-haves must be genuinely non-negotiable — an
   unevidenced must eliminates everything unknown.)
5. **Deadline unmet.** The item verifiably cannot arrive by the user's
   needed-by date — OR the deadline cannot be verified either way when a
   deadline exists (latest confirmed delivery date, where it can be
   computed, must be on or before the deadline).

When a notable candidate is eliminated, remember the reason — the
presentation says which strong candidates fell to which filter.

## Step 2 — Weighted soft scoring

Every requirement in the brief is classified by importance, and every
candidate is scored per requirement by match quality.

**Importance weights:**

| Importance   | Weight |
|--------------|--------|
| `must`       | 40     |
| `core`       | 30     |
| `preference` | 20     |
| `nice`       | 10     |

**Match values:**

| Match      | Value |
|------------|-------|
| `strong`   | 1.0   |
| `partial`  | 0.5   |
| `unknown`  | 0.25  |
| `none`     | 0.0   |

Rules:

- A requirement with **no evidence** for a candidate counts as `unknown`
  (0.25) — never as a match, never silently dropped.
- `none` (confirmed miss) scores below `unknown` (unresolved): a
  confirmed negative is worse than an open question.
- Compute: `fit_score = sum(weight × match_value) / sum(weight over ALL
  requirements)`. All requirements in the brief participate, including
  ones with no evidence.
- The result is a 0-1 fit score per surviving candidate.

## Step 3 — Sort order (deterministic)

Rank survivors by, in order:

1. `fit_score` — descending
2. `price` — ascending (unknown prices sort last)
3. `name` — ascending, case-insensitive
4. `URL` — ascending (final tiebreak, makes order fully deterministic)

Ties at every level are broken by the next key; identical input always
produces identical output.

## Step 4 — Present 2-4 options, short and human

Present the top 2-4. Fewer than 2 only when research genuinely surfaced
fewer viable candidates — say so rather than padding with weak ones.

Voice: plain, short, conversational — like texting a knowledgeable
friend. No method talk, no scoring jargon (never mention fit_score,
weights, strong/partial/none/unknown). No preamble about how you
searched. No repeating the same fact in two places. Keep every wrapper
sentence under ~20 words. The product itself is the one place you do
NOT trim — give its full detail.

Shape (adapt naturally, not a rigid template):

I found [N] good options for you:

1. **[Name]** — 1-2 sentences on what it is and why it fits THIS user.
   - Pros: 1-3 short bullets, only what matters to their brief.
   - Cons: 1-2 honest minuses (cost vs. alternatives, reviewer
     complaints, weight/looks/durability — whatever matters).
   - $62 at ExampleMart (seen 2026-09-09) — [link]
   - Flag anything unverified inline, briefly: "availability
     unconfirmed — check the listing."

2. ... (same shape)

I'd go with [#N] because [1-2 plain reasons tied to their brief].

After the options, only if needed:

- **Filter transparency** — one short clause, only when a notable
  candidate was cut ("Skipped BrandY — $15 over budget."). Omit
  entirely if nothing notable was cut.
- **Never fabricate.** No invented products, prices, availability,
  ratings, or specifications. Every factual claim traces to a source URL
  or is labeled unverified.

Conciseness never drops required facts: every option still carries
name + what it is, observed price + date, why it fits, honest
trade-offs, unverified flags, and the verified direct link. Trim words,
never facts.

## Step 5 — Feedback invite (lightweight)

End the recommendation with **one brief line**, e.g.:

> "If you end up buying one of these, let me know how it works out — it
> helps me recommend better next time."

Rules:

- One line, once, at presentation time. Never repeated.
- **No proactive follow-ups afterwards.** Don't check in later, don't
  ask again in a future session.
- The feedback loop is **passive**: it only records what the user
  volunteers.

## Passive feedback loop

When the user later mentions — unprompted — an outcome of something you
recommended ("the pillow you suggested worked great", "returned the
laptop, too heavy"):

1. **Record the outcome** — what was bought, kept, returned, or
   disliked, per the memory rules in [memory-privacy.md](memory-privacy.md).
2. **Use it to shape future recommendations** in the same category — a
  "too firm" outcome should push future pillow recommendations toward
   softer options for this user; a brand return should down-weight that
   brand. This is user-reported evidence, the strongest kind.
3. Don't turn it into a survey. Acknowledge briefly and move on.

## Script usage

For script-capable hosts, run the helper rather than scoring by hand:

```
python3 scripts/rank_candidates.py <task.json>   # or JSON piped to stdin
```

with `task.json` shaped as:

```json
{
  "brief": {"budget": {"maximum": 80, "currency": "USD"}, "region": "US",
             "avoid": ["BrandX"], "deadline": null},
  "requirements": [
    {"requirement": "firm support", "importance": "must"},
    {"requirement": "cooling", "importance": "preference"}
  ],
  "candidates": [
    {"name": "...", "product_url": "...", "seller_or_manufacturer": "...",
     "observed_price": 62.0, "currency": "USD", "observed_at": "2026-09-09",
     "ships_to_region": true, "delivery_days_max": 4,
     "criteria": [
       {"requirement": "firm support", "importance": "must",
        "match": "strong", "source_urls": ["..."]}
     ],
     "tradeoffs": ["..."]}
  ]
}
```

The script applies the same hard filters, the same weights and match
values, and the same four-key sort, and returns the top 4 plus
filter-reasons for eliminated candidates. If its output ever disagrees
with this prose spec, the spec wins and the script is buggy.