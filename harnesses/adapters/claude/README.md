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

### Claude Code

```bash
npx skills add <owner>/<repo>
```

Or, if you cloned the repo manually, copy this directory's contents into `~/.claude/skills/openconcierge/` and restart Claude Code.

### Claude Desktop

Open Claude Desktop → Settings → Capabilities → Skills → "+" → search "openconcierge" → Install.

### claude.ai Chat

Open the Skills marketplace in claude.ai → search "openconcierge" → Install. The skill is project-scoped by default; promote to global from Settings → Skills.

## How it works

The skill is content-only — no background service, no MCP server, no hosted API. All computation happens inside Claude. A small `scripts/rank_candidates.py` is included for the agent to invoke when it needs a deterministic ranking.

## License

MIT. See `LICENSE` at the repository root.
