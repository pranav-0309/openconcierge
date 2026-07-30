# Memory and Privacy

This document expands the `## Memory and Privacy` section of `SKILL.md`. OpenConcierge uses only the host agent's memory; it does not introduce a separate database, vector index, or persistence layer.

## Confirmation

Stable shopping preferences are persisted only after the user explicitly confirms them. Transient task details, browsing history, and unconfirmed inferences are never promoted to long-term preferences.

## What may be stored

After explicit confirmation, stable shopping preferences may include:

- Preferred or avoided brands.
- Common sizing.
- Budget sensitivity.
- Preferred materials or product characteristics.
- Region and currency.
- Recurring compatibility constraints.

## Sensitive constraints

Health information, allergies, disability-related needs, and other sensitive constraints are used for the current task only. They are not stored as durable preferences unless the user explicitly asks for that behavior. When a sensitive constraint could affect safety or suitability, surface it in the current recommendation and ask the user whether to remember it.

## User controls

The skill supports these requests in natural language or as arguments to `/openconcierge`:

- `show preferences` — list currently stored shopping preferences.
- `correct preference` — update or replace a stored preference after confirmation.
- `forget preference` — remove a single named shopping preference.
- `forget all preferences` — remove every namespaced shopping preference.
