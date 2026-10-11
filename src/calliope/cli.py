"""Typer CLI for Calliope."""

from __future__ import annotations

import asyncio

import typer
from agentkit import build_deps, build_model, build_runtime, repositories
from agentkit.session import ChatRunner

from calliope import __version__
from calliope.config import get_settings
from calliope.db.repos import Repositories
from calliope.services import journal as svc

app = typer.Typer(
    add_completion=False,
    help="Calliope — a daily journaling and ESL English-writing coach.",
    no_args_is_help=True,
)


def _runtime():
    return build_runtime(get_settings(), repos_factory=Repositories)


def _enable_observability() -> None:
    from agentkit.observability import setup_observability

    setup_observability(get_settings())


@app.command()
def version() -> None:
    """Print the Calliope version."""
    typer.echo(f"calliope {__version__}")


@app.command()
def entry(
    text: str = typer.Argument(..., help="The journal entry text."),
    title: str | None = typer.Option(None, help="Optional title."),
    mood: int | None = typer.Option(None, min=1, max=5, help="Mood 1–5."),
    tag: list[str] = typer.Option([], "--tag", help="Tag (repeatable)."),
    date: str | None = typer.Option(None, "--date", help="ISO date; defaults to today."),
) -> None:
    """Record a journal entry (no LLM needed)."""
    runtime = _runtime()
    with repositories(runtime) as repos:
        deps = build_deps(runtime, repos)
        saved = svc.record_entry(deps, text, title=title, mood=mood, tags=tag, entry_date=date)
        stats = svc.journal_stats(deps)
    typer.echo(
        f"saved entry #{saved.id} for {saved.entry_date} ({saved.word_count} words). "
        f"streak: {stats.current_streak} days"
    )


@app.command("list")
def list_command(limit: int = typer.Option(10, "--limit")) -> None:
    """List recent journal entries."""
    runtime = _runtime()
    with repositories(runtime) as repos:
        deps = build_deps(runtime, repos)
        rows = svc.list_entries(deps, limit)
    if not rows:
        typer.echo("no entries yet")
        return
    for row in rows:
        mood = f" mood={row.mood}" if row.mood else ""
        typer.echo(f"{row.entry_date}  ({row.word_count}w){mood}  {row.title or row.body[:60]}")


@app.command()
def stats() -> None:
    """Show streak, totals and words this week."""
    runtime = _runtime()
    with repositories(runtime) as repos:
        deps = build_deps(runtime, repos)
        summary = svc.journal_stats(deps)
    typer.echo(f"entries: {summary.total_entries}")
    typer.echo(f"current streak: {summary.current_streak} days")
    typer.echo(f"total words: {summary.total_words} (this week: {summary.words_this_week})")
    if summary.avg_mood is not None:
        typer.echo(f"average mood: {summary.avg_mood:.1f}")
    if summary.last_entry_date is not None:
        typer.echo(f"last entry: {summary.last_entry_date}")


@app.command()
def critique(
    text: str = typer.Argument(..., help="English text to review."),
    level: str | None = typer.Option(None, help="Your CEFR level (A1–C2)."),
) -> None:
    """Review your English and save structured feedback (uses the model)."""
    runtime = _runtime()
    with repositories(runtime) as repos:
        deps = build_deps(runtime, repos, model=build_model(runtime.settings))
        submission = svc.start_submission(deps, text, level)
        from calliope.agents.writing import writing_agent

        prompt = "Review and correct this English writing"
        if level:
            prompt += f" (writer's stated level: {level})"
        result = asyncio.run(
            writing_agent.run(f"{prompt}:\n\n{text}", deps=deps, model=deps.model)
        )
        critique_model = result.output
        if submission.id is not None:
            svc.save_critique(deps, submission.id, critique_model)
    typer.echo(svc.format_critique(critique_model))


@app.command()
def chat(conv: str = typer.Option("cli:default", help="Conversation id.")) -> None:
    """Interactive chat with Calliope."""
    _enable_observability()
    asyncio.run(_chat(conv))


async def _chat(conv: str) -> None:
    from calliope.agents.orchestrator import orchestrator_agent

    runtime = _runtime()
    typer.echo(f"Calliope ({conv}). Type 'exit' to quit.")
    while True:
        try:
            text = await asyncio.to_thread(input, "you> ")
        except (EOFError, KeyboardInterrupt):
            break
        text = text.strip()
        if text in {"exit", "quit", ":q"}:
            break
        if not text:
            continue
        with repositories(runtime) as repos:
            deps = build_deps(runtime, repos, model=build_model(runtime.settings))
            runner = ChatRunner(deps, agent=orchestrator_agent, conversation_id=conv)
            result = await runner.send(text)
        typer.echo(f"calliope> {result.output}")


@app.command()
def soul(
    init: bool = typer.Option(False, "--init", help="Write a default SOUL.md if missing."),
) -> None:
    """Show the active SOUL.md persona (or scaffold one with --init)."""
    from calliope.soul import ensure_soul, load_soul, resolve_soul_path

    settings = get_settings()
    if init:
        typer.echo(f"wrote {ensure_soul(settings)}")
        return
    typer.echo(f"# {resolve_soul_path(settings)}")
    typer.echo(load_soul(settings))


@app.command()
def up(
    a2a: bool = typer.Option(True, "--a2a/--no-a2a", help="Run the A2A server."),
    mcp: bool = typer.Option(True, "--mcp/--no-mcp", help="Run the MCP HTTP server."),
) -> None:
    """Run the whole stack in one process (A2A + MCP + observability)."""
    from agentkit.supervise import Service, run_all

    settings = get_settings()
    if not (a2a or mcp):
        typer.echo("nothing to run")
        return
    _enable_observability()
    runtime = _runtime()

    services: list[Service] = []
    if a2a:
        services.append(Service("a2a", lambda: _serve_a2a(settings, runtime)))
    if mcp:
        services.append(Service("mcp", lambda: _serve_mcp(settings, runtime)))
    typer.echo("calliope up: " + ", ".join(service.name for service in services))
    run_all(services)


def _answer(settings, runtime):
    from calliope.agents.orchestrator import orchestrator_agent

    async def answer(text: str) -> str:
        with repositories(runtime) as repos:
            deps = build_deps(runtime, repos, model=build_model(settings))
            runner = ChatRunner(deps, agent=orchestrator_agent, conversation_id="a2a:default")
            return (await runner.send(text)).output

    return answer


def _serve_a2a(settings, runtime) -> None:
    from agentkit.a2a import (
        SQLAlchemyTaskStore,
        TaskAgentExecutor,
        build_a2a_app,
        build_card,
        serve_a2a,
    )

    card = build_card(
        name=settings.a2a_card_name,
        description="Calliope — daily journaling and ESL English-writing coach.",
        url=settings.a2a_public_url,
        skills=[{"id": "journaling", "name": "Journaling", "tags": ["journal", "reflection"]},
                {"id": "esl-writing", "name": "ESL writing coach", "tags": ["english", "esl"]}],
    )
    app = build_a2a_app(
        card=card,
        executor=TaskAgentExecutor(_answer(settings, runtime)),
        task_store=SQLAlchemyTaskStore(runtime),
        healthz=lambda: True,
    )
    serve_a2a(app, host=settings.a2a_host, port=settings.a2a_port)


def _serve_mcp(settings, runtime) -> None:
    from agentkit.mcp.server import serve_mcp
    from fastmcp import FastMCP

    from calliope.agents.schemas import JournalEntryRecord, JournalStats

    server = FastMCP(name="calliope", instructions="Daily journaling and ESL writing coach.")

    @server.tool
    async def ask_calliope(prompt: str, conversation_id: str = "mcp:default") -> str:
        """Ask the full Calliope agent."""
        from calliope.agents.orchestrator import orchestrator_agent

        with repositories(runtime) as repos:
            deps = build_deps(runtime, repos, model=build_model(settings))
            runner = ChatRunner(deps, agent=orchestrator_agent, conversation_id=conversation_id)
            return (await runner.send(prompt)).output

    @server.tool
    def get_stats() -> JournalStats:
        """Journaling streak and totals."""
        with repositories(runtime) as repos:
            return svc.journal_stats(build_deps(runtime, repos))

    @server.tool
    def list_entries(limit: int = 10) -> list[JournalEntryRecord]:
        """Recent journal entries."""
        with repositories(runtime) as repos:
            deps = build_deps(runtime, repos)
            return [svc.to_record(entry) for entry in svc.list_entries(deps, limit)]

    serve_mcp(server, transport="streamable-http", host=settings.mcp_host, port=settings.mcp_port)


def main() -> None:
    from agentkit.logging import setup_logging

    setup_logging(get_settings())
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
