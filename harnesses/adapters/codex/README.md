# openconcierge

Research and compare products through a focused, source-backed shopping conversation.

OpenConcierge is a patient, evidence-oriented personal shopping concierge. It interviews you about your needs, finds source-backed candidates using your host agent's existing search tools, ranks them deterministically, and presents trade-offs honestly.

## What it does

- Asks only the clarifying questions whose answers change the outcome.
- Uses the host agent's built-in web search and MCP/plugin tool discovery — no provider keys required.
- Ranks candidates deterministically with a stdlib-only Python helper.
- Cites sources for every claim and labels unknowns as unknown.
- Remembers stable shopping preferences only after you confirm them.

## Install

### Codex CLI

Drop the unzipped skill folder into `~/.codex/skills/openconcierge/` (or `$CODEX_HOME/skills/openconcierge/` if `CODEX_HOME` is set) and restart Codex.

### Skills registry

```bash
npx skills add <owner>/<repo>
```

(`<owner>/<repo>` is filled in at release time. Until then, use the drop-in path.)

## How it works

The skill is content-only — no background service, no MCP server, no hosted API. All computation happens inside Codex. A small `scripts/rank_candidates.py` is included for the agent to invoke when it needs a deterministic ranking.

## License

MIT. See `LICENSE` at the repository root.