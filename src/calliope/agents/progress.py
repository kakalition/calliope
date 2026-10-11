"""Progress sub-agent: streaks, word counts and weekly reporting."""

from __future__ import annotations

from pydantic_ai import Agent, RunContext

from calliope.agents.deps import Deps
from calliope.agents.prompts import PROGRESS
from calliope.agents.schemas import JournalEntryRecord, JournalStats
from calliope.services import journal as svc

progress_agent = Agent(
    name="progress", deps_type=Deps, output_type=str, instructions=PROGRESS
)


@progress_agent.tool
async def get_stats(ctx: RunContext[Deps]) -> JournalStats:
    """Current streak, totals and words this week."""
    return svc.journal_stats(ctx.deps)


@progress_agent.tool
async def recent_entries(ctx: RunContext[Deps], limit: int = 7) -> list[JournalEntryRecord]:
    """Recent entries, for tone and continuity."""
    return [svc.to_record(entry) for entry in svc.list_entries(ctx.deps, limit)]
