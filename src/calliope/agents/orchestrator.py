"""Calliope's orchestrator: routes to journal / writing / progress."""

from __future__ import annotations

from agentkit.orchestrator import Orchestrator
from pydantic_ai import RunContext

from calliope.agents.deps import Deps
from calliope.agents.journal import journal_agent
from calliope.agents.progress import progress_agent
from calliope.agents.prompts import ORCHESTRATOR
from calliope.agents.writing import writing_agent
from calliope.services import journal as svc
from calliope.soul import compose_instructions, load_soul

_orchestrator = Orchestrator(
    name="calliope",
    instructions=compose_instructions(load_soul(), ORCHESTRATOR),
    deps_type=Deps,
)
_orchestrator.add_specialist(
    journal_agent,
    tool_name="handle_journal",
    description="Record or list journal entries and report the streak.",
)
_orchestrator.add_specialist(
    progress_agent,
    tool_name="handle_progress",
    description="Report journaling streaks, word counts and weekly progress.",
)

orchestrator_agent = _orchestrator.agent


@orchestrator_agent.tool
async def handle_writing(
    ctx: RunContext[Deps], text: str, level: str | None = None
) -> str:
    """Review the writer's English and save the feedback.

    Args:
        text: The writer's text, verbatim.
        level: Their stated CEFR level (A1–C2), if given.
    """
    submission = svc.start_submission(ctx.deps, text, level)
    prompt = "Review and correct this English writing"
    if level:
        prompt += f" (writer's stated level: {level})"
    prompt += f":\n\n{text}"
    result = await writing_agent.run(
        prompt, deps=ctx.deps, usage=ctx.usage, model=ctx.deps.model
    )
    critique = result.output
    if submission.id is not None:
        svc.save_critique(ctx.deps, submission.id, critique)
    return svc.format_critique(critique)
