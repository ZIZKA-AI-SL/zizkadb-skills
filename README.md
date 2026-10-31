# ZizkaDB skills for coding agents

> Part of **[ZizkaDB](https://github.com/ZIZKA-AI-SL/ZizkaDB)**, the open-source causal database for AI agents.

[![OpenSSF Baseline](https://www.bestpractices.dev/projects/16048/baseline)](https://www.bestpractices.dev/projects/16048)
[![ZizkaDB](https://img.shields.io/github/stars/ZIZKA-AI-SL/ZizkaDB?label=ZizkaDB&style=flat)](https://github.com/ZIZKA-AI-SL/ZizkaDB)

Two skills that let your coding agent answer the hard questions about *your* AI agent, from its recorded history instead of guesses:

| Skill | Ask your coding agent | What you get |
|-------|----------------------|--------------|
| **zizkadb-why** | "Why did my agent call `refund`?" · "Why did the agent fail?" | The causal chain from the action back to its root cause, in plain language |
| **zizkadb-audit** | "Prove the agent's logs weren't changed" · "Prepare EU AI Act evidence" | Hash-chain check per agent, exported history with SHA-256, and `report.md` / `report.json` |

The plugin also connects the [ZizkaDB MCP server](https://github.com/ZIZKA-AI-SL/ZizkaDB/tree/main/mcp) (`uvx zizkadb-mcp`), so your coding agent can log, search and time-travel too.

## Install (Claude Code)

```
/plugin marketplace add ZIZKA-AI-SL/zizkadb-skills
/plugin install zizkadb@zizkadb
```

Then just ask, for example: *"Why did my support agent call lookup_order?"*

**No ZizkaDB yet?** The skill offers to start the open-source one locally (one Docker container, about a minute, data stays on your machine). It comes with a demo agent run, so you see a real answer straight away. Then connect your own agent with three lines: [CONNECT.md](https://github.com/ZIZKA-AI-SL/ZizkaDB/blob/main/CONNECT.md).

**Already running ZizkaDB?** Set `ZIZKADB_HOST` (and `ZIZKADB_API_KEY` for a non-local instance) in your environment before starting your coding agent.

## Other coding agents

The skills are plain `SKILL.md` files in [`plugins/zizkadb/skills/`](plugins/zizkadb/skills), with a standard-library Python helper in [`plugins/zizkadb/scripts/zizkadb.py`](plugins/zizkadb/scripts/zizkadb.py). Agents that read `SKILL.md` files can use them directly; the helper also works on its own:

```bash
python3 plugins/zizkadb/scripts/zizkadb.py status        # is ZizkaDB reachable?
python3 plugins/zizkadb/scripts/zizkadb.py why <event_id>
python3 plugins/zizkadb/scripts/zizkadb.py audit --out zizkadb-audit
```

## In CI

The same answers on every pull request, as GitHub Actions:

- [ZizkaDB Why](https://github.com/marketplace/actions/zizkadb-why-explain-ai-agent-failures): causal chains of agent test failures in the PR
- [ZizkaDB Audit](https://github.com/marketplace/actions/zizkadb-audit-verify-ai-agent-history): hash-chain check and an attested audit report

## Good to know

- Open-source ZizkaDB records **one agent per install** (the demo agent does not count). Multiple agents, fleets and agent-to-agent recording: [ZizkaDB Cloud](https://db.zizka.ai).
- The ZizkaDB SDK and MCP server send an anonymous install count; set `ZIZKADB_TELEMETRY=false` to turn it off. [Details](https://github.com/ZIZKA-AI-SL/ZizkaDB/blob/main/docs/telemetry.md).

**[⭐ Star ZizkaDB on GitHub](https://github.com/ZIZKA-AI-SL/ZizkaDB)** · [Quickstart](https://github.com/ZIZKA-AI-SL/ZizkaDB#quickstart-60-seconds) · [Docs](https://db.zizka.ai/docs)

---

MIT licensed. Security issues: founder@zizka.ai ([policy](https://github.com/ZIZKA-AI-SL/ZizkaDB/blob/main/SECURITY.md)).
