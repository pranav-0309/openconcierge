# OpenConcierge

A source-backed shopping concierge **skill** for any AI product with a
skill-loading mechanism — Claude, ChatGPT, Codex, OpenCode, Hermes Agent,
OpenClaw, and more.

OpenConcierge interviews you about what you want to buy, researches the
live web through whatever search capability your AI already exposes, and
recommends 2–4 sourced options ranked deterministically by fit to your
needs and budget. Your AI owns the model, search, memory, and interface —
OpenConcierge owns only the shopping conversation, evidence rules, and
ranking logic.

**Current release: 0.1.4** — check [CHANGELOG.md](CHANGELOG.md). If you
installed by uploading a ZIP (claude.ai, Claude Desktop, ChatGPT), you
will not receive automatic updates; compare your `SKILL.md` version
against this README to notice when you're outdated.

## What it does

1. Parses your request into a shopping brief (category, problems,
   must-haves, preferences, avoid list, budget, region).
2. Asks only decision-relevant follow-up questions — and stops once a
   useful search is possible. Accepts "use your judgment".
3. Researches the live web through your AI's existing search tools
   (built-in web search, page extraction, or any MCP/plugin search).
   Never fabricates results.
4. Verifies candidates against direct product/manufacturer pages,
   applies review skepticism, and labels what it couldn't verify.
5. Hard-filters (budget, region, exclusions, must-haves, deadline), then
   ranks with a transparent weighted rule and presents 2–4 options with
   rationale, trade-offs, and direct links.
6. Persists what it learns about you to your AI's own memory
   (write-only; never touches unrelated memories).

## How to invoke it

Skills are **model-invoked**: the AI decides when to use one based on its
description. Auto-invocation is best-effort on every host and can be
inconsistent (claude.ai in particular often waits to be told). When you
want to be sure, just name it:

> "Use OpenConcierge to find me a mechanical keyboard under $150."

Typing the skill name always triggers it. You can also ask the AI
"which skills are available?" to confirm OpenConcierge is loaded.

## Install

The skill lives in `skills/openconcierge/` — a fully self-contained
folder that installs natively on every major agent.

| Host | Install |
|---|---|
| **Any (universal)** | `npx skills add <owner>/<repo>` (auto-detects installed agents; supports `--skill`, `-a <agent>`, `--list`) |
| **Claude Code** | `/plugin marketplace add <owner>/<repo>` → `/plugin install openconcierge`, or copy `skills/openconcierge/` into `~/.claude/skills/` (global) or `.claude/skills/` (project) |
| **claude.ai / Claude Desktop** | Download the release ZIP; Settings → Customize → Skills → Upload (the ZIP has the skill folder at its root) |
| **ChatGPT (web)** | Profile icon → Skills → New skill → Upload from computer → select `SKILL.md` or the skill-folder ZIP |
| **Codex** | Copy `skills/openconcierge/` into `~/.codex/skills/` (global) or `.codex/skills/` / `.agents/skills/` (project); in-session: `$skill-installer install <repo-url>/tree/main/skills/openconcierge` |
| **OpenCode** | Copy `skills/openconcierge/` into `.opencode/skills/`, `.agents/skills/`, or `.claude/skills/` (project) or `~/.config/opencode/skills/` (global) |
| **Hermes Agent** | `hermes skills install <raw-SKILL.md-url>`, or `/skills install <identifier>` in chat; teams: point `HERMES_OPTIONAL_SKILLS_DIR` at the repo's `skills/` |
| **OpenClaw** | `openclaw skills install skills-sh:<owner>/<repo>/openconcierge` or `npx clawhub@latest install --git <repo-url>.git` |
| **Cursor / Copilot / Cline / Gemini CLI** | Copy `skills/openconcierge/` into `.agents/skills/` |

## Build a release ZIP

Requires Python 3:

```
python scripts/build_zip.py     # from the repo root
```

produces `dist/openconcierge.zip` with the `openconcierge/` folder at the
zip root, ready to upload to claude.ai, Claude Desktop, or ChatGPT.

## Tests

The deterministic ranking helper (`skills/openconcierge/scripts/rank_candidates.py`)
is tested with pytest; no test makes a network call:

```
python -m pytest skills/openconcierge/scripts/tests/
```

## License

MIT — see [LICENSE](LICENSE).