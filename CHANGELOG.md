# Changelog

All notable changes to OpenConcierge are documented here. The version here
matches the `version` field in `skills/openconcierge/SKILL.md`.

## 0.1.1 — 2026-09-09

- Fix OpenCode skill-invocation bug: a dollar-amount example in SKILL.md
  (`under $1000`) matched OpenCode's `$N` command-template placeholder
  syntax, which swallowed the user's prompt when the skill was invoked as
  a slash command. Reworded so no `$<digits>` sequence appears in
  SKILL.md. Affects OpenCode only; other hosts never template skill
  content.

## 0.1.0 — 2026-09-09

Initial release.

- Provider-neutral `openconcierge` skill (`SKILL.md`) implementing the full
  concierge flow: shopping brief, decision-relevant interviewing, live-web
  research through host search, candidate verification with review
  skepticism, hard filtering, deterministic weighted ranking, 2–4 sourced
  recommendations with trade-offs, lightweight feedback invite, and
  write-only memory persistence to host memory.
- Four reference documents: interviewing, research/evidence,
  recommendation (prose scoring specification), memory/privacy.
- Deterministic ranking helper `scripts/rank_candidates.py` (standard
  library only, no network) with a pytest suite.
- Cross-agent repository layout: `skills/openconcierge/` +
  `.claude-plugin/marketplace.json`.
- Release ZIP builder producing `dist/openconcierge.zip` with the skill
  folder at the zip root for upload-based hosts.