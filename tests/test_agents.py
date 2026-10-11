from __future__ import annotations

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from calliope.agents.journal import journal_agent
from calliope.agents.orchestrator import orchestrator_agent
from calliope.agents.schemas import WritingCritique
from calliope.agents.writing import writing_agent


def _has_tool_return(messages: list[ModelMessage]) -> bool:
    return any(
        isinstance(part, ToolReturnPart)
        for message in messages
        for part in getattr(message, "parts", [])
    )


def _tool_names(agent) -> set[str]:
    return set(agent._function_toolset.tools.keys())


def test_orchestrator_registers_specialists():
    assert _tool_names(orchestrator_agent) >= {"handle_journal", "handle_writing", "handle_progress"}


def test_journal_agent_tools():
    assert _tool_names(journal_agent) >= {"add_entry", "list_entries", "get_stats"}


async def test_writing_agent_returns_structured_critique(deps):
    args = {
        "summary": "Clear and warm.",
        "corrected_text": "I went to school yesterday.",
        "corrections": [
            {"original": "goes", "corrected": "went", "explanation": "Past tense.", "category": "grammar"}
        ],
        "vocabulary": [{"word": "yesterday", "meaning": "the day before", "example": "I went yesterday."}],
        "next_steps": ["Practise past simple."],
        "estimated_level": "A2",
    }

    def model_fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        output_tools = getattr(info, "output_tools", None)
        name = output_tools[0].name if output_tools else "final_result"
        return ModelResponse(parts=[ToolCallPart(name, args)])

    deps.model = FunctionModel(model_fn)
    result = await writing_agent.run("I goes to school yesterday.", deps=deps, model=deps.model)
    assert isinstance(result.output, WritingCritique)
    assert result.output.estimated_level == "A2"
    assert result.output.corrections[0].corrected == "went"


async def test_orchestrator_delegates_to_journal(deps, repos):
    def model_fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        names = {tool.name for tool in info.function_tools}
        if "add_entry" in names:  # journal sub-agent
            if _has_tool_return(messages):
                return ModelResponse(parts=[TextPart("saved")])
            return ModelResponse(parts=[ToolCallPart("add_entry", {"body": "hello journal today"})])
        if _has_tool_return(messages):
            return ModelResponse(parts=[TextPart("done")])
        return ModelResponse(parts=[ToolCallPart("handle_journal", {"request": "write hello journal today"})])

    deps.model = FunctionModel(model_fn)
    result = await orchestrator_agent.run("write a journal entry", deps=deps, model=deps.model)
    assert result.output == "done"
    assert repos.journal.count() == 1
