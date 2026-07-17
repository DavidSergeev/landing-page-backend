import json
import logging
from typing import Any
import src.resources.constants as constant
from src.agent_auxiliary.agent_state import AgentState


def get_initial_state(query: str, max_iterations: int) -> AgentState:
    return AgentState(
        input=query,
        max_iterations=max_iterations
    )


def parse_llm_response(
    llm_response, logger: logging.Logger
) -> tuple[str, str, str | None, dict[str, Any]]:
    """
    Parse LLM response into (thoughts, action_type, tool_name, tool_kwargs).

    Expects a JSON object with keys action-type/thoughts/tool-name/tool-kwargs.
    Falls back to treating the raw content as a final answer when JSON is absent or malformed.
    """
    thoughts = f"{constant.FINAL_ANSWER_PREFIX}{llm_response.text}"
    action_type = constant.REASON
    tool_name: str = ""
    tool_kwargs: dict[str, Any] = {}

    try:
        parsed = json.loads(llm_response.text)
        thoughts = parsed.get("thoughts", thoughts)
        action_type = parsed.get("action-type", constant.REASON)
        tool_name = parsed.get("tool-name", "")
        tool_kwargs = parsed.get("tool-kwargs", {})
    except Exception as e:
        logger.exception("Unexpected error parsing LLM response: %s", e)

    return thoughts, action_type, tool_name, tool_kwargs
