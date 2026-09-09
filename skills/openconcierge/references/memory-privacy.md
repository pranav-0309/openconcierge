# Memory and Privacy Rules

OpenConcierge persists what it learns to **whatever memory the host
exposes**, using the host's own memory mechanism. If the host exposes no
memory, skip persistence gracefully — the shopping task itself must
never depend on memory being available.

## What to persist (write-only)

Persist **everything learned about the user that would tailor future
recommendations**:

- **Shopping preferences** — preferred and avoided brands, budget
  sensitivity, preferred materials, common sizing, typical categories.
- **Personal context relevant to product fit** — including health,
  allergy, or disability needs that shape what products suit them (e.g.
  "side sleeper with neck pain", "latex allergy", "narrow feet"). This
  context is persisted precisely because it makes future recommendations
  safer and better tailored; it is not "too sensitive" to remember.
- **Reported outcomes** — what was bought, kept, returned, or disliked
  from your recommendations, and why ("pillow too firm", "laptop was a
  keeper").
- **Region and currency**, if stable across tasks.

## Memory rules

1. **Write-only with one exception.** The skill writes new entries and
   may update or correct **its own prior shopping-related entries**
   (e.g. superseding "prefers medium-firm pillows" with "prefers soft
   pillows" after an outcome report).
2. **Never delete or modify host memories unrelated to shopping.** Not
   other skills' entries, not user notes, not anything the skill didn't
   write. No exceptions.
3. **Never ask the host to forget the user's other memories.** Not even
   on user request — decline and let the user manage their own memory
   through the host's own controls.
4. **Use the host's own memory mechanism** — whatever the session
   exposes (memory tool, notes file, profile store). Don't invent
   side-channels, don't write to random files, don't create "shadow
   memory" the user can't see or control.
5. **Keep entries factual and compact.** Record observed facts and
   user-stated preferences, not speculation. "User reported the CozyRest
   pillow was too firm for side sleeping (2026-09)" — not editorializing.

## Passive feedback loop

When the user unprompted reports an outcome ("the pillow worked great",
"I returned it, too firm"), record:

- what was bought (product name, and URL if known)
- the outcome: kept / returned / disliked / loved
- the stated reason, if any
- the date

Then use it: outcomes are the strongest preference evidence — future
recommendations in the same category should shift accordingly (see
[recommendation.md](recommendation.md)).

## Credentials and secrets

- **Never read, write, or transmit credentials** of any kind — API keys,
  tokens, passwords, session cookies. The host owns all credentials.
- Never store payment details, addresses, or account identifiers.
  Shopping recommendations need none of them.

## Telemetry

- **No third-party telemetry. Ever.** Nothing the skill learns leaves
  the host's own memory. No analytics, no "phone-home", no usage
  tracking, no crash reporting.
- Everything persists only in the host's memory and is subject to the
  host's memory controls — that's the point.

## Applying memory on later tasks

- On a new shopping task, read what memory the host exposes and use
  recorded preferences silently (never re-ask what you know).
- If memory conflicts with what the user just said, **the conversation
  wins** — and update your own prior entry accordingly.
- Don't dump memory contents at the user unprompted; use it, don't
  recite it.