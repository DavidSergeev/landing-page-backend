from typing import Any, Union
from src.agent_auxiliary.agent_state import AgentState


def get_initial_state(query: str, max_iterations: int) -> AgentState:
    return AgentState(
        input=query,
        max_iterations=max_iterations
    )


def extract_text_content(content: Union[str, list[Any]]) -> str:
    """
    Extract plain text from a LangChain message's `content` field.

    `content` is a plain string for most providers, but Gemini may emit a list of
    content blocks (e.g. text/thinking/tool parts) instead; only the "text" blocks
    are concatenated and returned.
    """
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)
