import json
import logging
import src.resources.constants as constant
from src.agent_auxiliary.agent_state import AgentState


def get_initial_state(query: str, max_iterations: int) -> AgentState:
    return AgentState(
        input=query,
        max_iterations=max_iterations
    )


def parse_llm_response(llm_response, logger: logging.Logger) -> tuple[str, str | None, str | None]:
    """
    Parse LLM response into (thought, action, action_input).

    Expects JSON with keys thought/action/action_input for tool-use steps.
    Falls back to treating the raw content as a final answer when JSON is absent.
    """
    thought = constant.FINAL_ANSWER
    action: str | None = None
    action_input: str | None = None

    try:
        content = llm_response.content if isinstance(llm_response.content, str) else str(llm_response)
        content = content.strip()

        # Strip markdown code fences if the model wraps JSON in them
        if content.startswith("```"):
            lines = content.splitlines()
            content = "\n".join(lines[1:-1]).strip()

        parsed = json.loads(content)
        thought = parsed.get("thought", constant.FINAL_ANSWER)
        action = parsed.get("action")
        action_input = parsed.get("action_input")

    except (json.JSONDecodeError, AttributeError):
        # Plain-text response — treat as the final answer text
        raw = llm_response.content if isinstance(llm_response.content, str) else str(llm_response)
        action_input = raw.strip()

    except Exception as e:
        logger.exception("Unexpected error parsing LLM response: %s", e)

    return thought, action, action_input
