# openconcierge

Research and compare products through a focused, source-backed shopping conversation.

OpenConcierge is a patient, evidence-oriented personal shopping concierge. It interviews you about your needs, finds source-backed candidates using your host agent's existing search tools, ranks them deterministically, and presents trade-offs honestly.

## What it does

- Asks only the clarifying questions whose answers change the outcome.
- Uses the host agent's built-in web search and MCP/plugin tool discovery - no provider keys required.
- Ranks candidates deterministically with a stdlib-only Python helper.
- Cites sources for every claim and labels unknowns as unknown.
- Remembers stable shopping preferences only after you confirm them.

## Install

### Workspace (default)

```bash
openclaw skills install @<owner>/openconcierge
```

Installs into the active workspace's `skills/` directory, visible to that workspace's agent.

### Shared managed (--global)

```bash
openclaw skills install @<owner>/openconcierge --global
```

Installs into `~/.openclaw/skills/openconcierge/`, visible to all local agents on the machine.

### Drop-in

Drop the unzipped skill folder into `~/.openclaw/skills/openconcierge/` (or `<workspace>/skills/openconcierge/`) and restart OpenClaw. Honors `OPENCLAW_STATE_DIR` if set.

### Git install

```bash
openclaw skills install git:<owner>/<repo>@<ref>
```

`@<owner>/<repo>` and the ClawHub slug are filled in at release time. Until then, use the drop-in or Git install.

## How it works

The skill is content-only - no background service, no MCP server, no hosted API. All computation happens inside OpenClaw. A small `scripts/rank_candidates.py` is included for the agent to invoke when it needs a deterministic ranking.

## License

MIT. See `LICENSE` at the repository root.