# Calliope

**A daily journaling companion and an English (ESL) writing coach** — keep a
streak, get gentle, specific feedback on your English, and watch your words add
up — from a CLI, a Telegram bot, an MCP server, and an A2A endpoint.

Built on [**agentkit**](https://github.com/kakalition/agentkit) (PydanticAI v2 +
durable execution + MCP/A2A). Calliope is the journaling/writing domain; agentkit
is the plumbing.

[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
![License](https://img.shields.io/badge/license-MIT-green)

> Calliope is a writing coach, not a therapist or a doctor. It stays supportive
> and suggests real help when a topic is heavy.

---

## Why Calliope

- **A habit, not a chore.** Write a few lines a day; Calliope keeps the streak and
  the gentle nudge when you miss one.
- **Feedback that teaches.** Corrected text, categorised fixes, vocabulary to
  keep, and next steps — graded to your CEFR level, in your own voice.
- **Durable and private.** Everything runs locally on your machine; entries and
  feedback are stored in a local database you own.
- **Reachable everywhere.** CLI, Telegram, MCP, and A2A — plus an operator web UI.
- **Composable.** Built on [agentkit](https://github.com/kakalition/agentkit), so
  it inherits durable execution, approvals, audit, and observability.

## Table of contents

- [Why Calliope](#why-calliope)
- [What it does](#what-it-does)
- [Install](#install)
- [Configure](#configure)
- [CLI](#cli)
- [Web UI](#web-ui)
- [How the agents are organised](#how-the-agents-are-organised)
- [MCP & A2A](#mcp--a2a)
- [Persona (`SOUL.md`)](#persona-soulmd)
- [Observability](#observability)
- [Development](#development)
- [License](#license)

## What it does

- **Daily journaling** — record entries with an optional title, mood (1–5) and
  tags; keep a streak; see words this week and a mood trend.
- **ESL writing coach** — paste any English; Calliope returns a corrected version,
  a categorised list of changes (grammar / spelling / word choice / punctuation /
  style), 2–4 vocabulary items, next steps, and an estimated CEFR level — while
  keeping your voice and meaning.
- **Progress** — streaks, totals and weekly reporting, with a non-judgemental
  nudge when you miss a day.
- **Durable by default** — turns are checkpointed (DBOS on local SQLite) and the
  full stack runs in one process.

## Install

```bash
git clone https://github.com/kakalition/calliope && cd calliope
./install.sh                 # uv sync (incl. the local Phoenix observability UI)
cp .env.example .env         # then set OPENAI_API_KEY
```

Requires **Python 3.11–3.12** and [uv](https://docs.astral.sh/uv/). Calliope
depends on `agentkit` (installed from the sibling checkout via
`[tool.uv.sources]`).

### Quickstart

```bash
export OPENAI_API_KEY=sk-...                      # or put it in .env
uv run calliope entry "Today I practised English." --mood 4
uv run calliope critique "I goes to school yesterday."
uv run calliope up                                # A2A + MCP + web UI (:8787)
```

## Configure

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | – | Model credential |
| `OPENAI_BASE_URL` | – | Any OpenAI-compatible gateway |
| `MODEL_NAME` | `openai:gpt-4o-mini` | Model id |
| `OWNER_ID` / `OWNER_NAME` | `owner` / `Writer` | The writer |
| `AGENTKIT_HOME` | `~/.agentkit` | Workspace root (`~/.agentkit/calliope`) |
| `AGENT_HOME` | `~/.agentkit/calliope` | Explicit home override |
| `WEBUI_ENABLED` / `WEBUI_HOST` / `WEBUI_PORT` | `true` / `127.0.0.1` / `8787` | Operator web UI |
| `DEFAULT_ESL_LEVEL` | `B1` | CEFR level used when unspecified |
| `DAILY_WORD_GOAL` | `150` | Soft daily writing goal |
| `OBSERVABILITY` | `phoenix` | `phoenix` (local UI) \| `console` \| `otlp` \| `off` |
| `TELEGRAM_BOT_TOKEN` | – | Enables the bot |
| `A2A_PUBLIC_URL` / `A2A_HOST` / `A2A_PORT` | `http://127.0.0.1:9100` | A2A |
| `MCP_HOST` / `MCP_PORT` | `127.0.0.1` / `8860` | MCP HTTP |

## CLI

```bash
calliope entry "Today I practised writing." --title "Day 1" --mood 4 --tag esl
calliope list --limit 10
calliope stats
calliope critique "I goes to school yesterday." --level A2
calliope chat
calliope soul [--init]
calliope up                 # one process: A2A + MCP + web UI + observability
```

`entry`, `list` and `stats` are deterministic (no model). `critique` and `chat`
use the model.

## Web UI

`calliope up` also serves an operator web UI at `http://127.0.0.1:8787` (loopback,
no auth) for **this agent only**: inspect conversations/chat, usage, audit, A2A
tasks and durable workflows; manage schedules, edit the SOUL persona, view config
(secrets masked) and artifacts. Chat runs through the same orchestrator as the
CLI, so history is shared. Data now lives under `~/.agentkit/calliope` (run
`agentkit workspace migrate calliope` if upgrading from the old shared home).

## How the agents are organised

An orchestrator routes to three specialists (see
[agentkit](https://github.com/kakalition/agentkit) for the pattern):

| Specialist | Tools | Notes |
| --- | --- | --- |
| **journal** | `add_entry`, `list_entries`, `get_stats` | Records entries (audited) |
| **writing** | *(structured output)* | Returns a typed `WritingCritique` |
| **progress** | `get_stats`, `recent_entries` | Streaks, totals, weekly trends |

The orchestrator's `handle_writing` tool saves the submission and the critique,
so feedback is durable and reviewable.

## MCP & A2A

`calliope up` exposes Calliope over both protocols, in one process:

- **MCP** (`http://127.0.0.1:8860/mcp`): `ask_calliope`, `get_stats`,
  `list_entries`.
- **A2A** (`http://127.0.0.1:9100`): agent card + JSON-RPC, task-based, with a
  durable task store.

Point another agent (Hermes, nanobot, …) at either endpoint to let it journal or
review English through Calliope.

## Persona (`SOUL.md`)

Calliope's identity and coaching style live in `SOUL.md` (project root, else
`$AGENT_HOME/SOUL.md`) and are composed with the routing instructions.

```bash
calliope soul          # show
calliope soul --init   # scaffold
```

## Observability

**On by default** with a local **Arize Phoenix** UI (self-hosted, no account);
falls back to console spans if Phoenix isn't installed. Set `OBSERVABILITY=otlp`
to export to Jaeger/Tempo/Langfuse/a collector.

## Development

```bash
uv sync --extra dev
uv run pytest            # 13 tests
uv run ruff check src tests
uv run mypy src/calliope
```

Layout: `config`, `soul`, `cli`; `db/` (models, repos); `services/journal.py`;
`agents/` (journal, writing, progress, orchestrator, prompts, schemas, deps).

## License

MIT.
