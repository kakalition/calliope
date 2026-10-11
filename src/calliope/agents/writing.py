"""Writing sub-agent: structured ESL feedback (output_type = WritingCritique)."""

from __future__ import annotations

from pydantic_ai import Agent

from calliope.agents.deps import Deps
from calliope.agents.prompts import WRITING
from calliope.agents.schemas import WritingCritique

writing_agent = Agent(
    name="writing",
    deps_type=Deps,
    output_type=WritingCritique,
    instructions=WRITING,
)
