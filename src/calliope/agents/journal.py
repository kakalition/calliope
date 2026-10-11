"""Journal sub-agent: record, list and summarise entries."""

from __future__ import annotations

from pydantic_ai import Agent, RunContext

from calliope.agents.deps import Deps
from calliope.agents.prompts import JOURNAL
from calliope.agents.schemas import JournalEntryRecord, JournalStats
from calliope.services import journal as svc

journal_agent = Agent(
    name="journal", deps_type=Deps, output_type=str, instructions=JOURNAL
)


@journal_agent.tool
async def add_entry(
    ctx: RunContext[Deps],
    body: str,
    title: str | None = None,
    mood: int | None = None,
    tags: list[str] | None = None,
    entry_date: str | None = None,
) -> JournalEntryRecord:
    """Record a journal entry.

    Args:
        body: The entry text.
        title: Optional title.
        mood: Optional mood, 1 (low) to 5 (great).
        tags: Optional tags.
        entry_date: ISO date (YYYY-MM-DD); defaults to today.
    """
    entry = svc.record_entry(
        ctx.deps, body, title=title, mood=mood, tags=tags, entry_date=entry_date
    )
    return svc.to_record(entry)


@journal_agent.tool
async def list_entries(ctx: RunContext[Deps], limit: int = 10) -> list[JournalEntryRecord]:
    """List recent journal entries (newest first)."""
    return [svc.to_record(entry) for entry in svc.list_entries(ctx.deps, limit)]


@journal_agent.tool
async def get_stats(ctx: RunContext[Deps]) -> JournalStats:
    """Current streak, totals and words this week."""
    return svc.journal_stats(ctx.deps)
