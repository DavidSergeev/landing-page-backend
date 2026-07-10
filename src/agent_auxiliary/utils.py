import src.resources.constants as constant
from src.agent_auxiliary.agent_state import AgentState
import json

def get_initial_state(query: str, max_iterations: int) -> AgentState:
    return AgentState(
        input=query,
        max_iterations=max_iterations
    )

def parse_llm_response(llm_response, logger):
    thought, action_input, action = constant.FINAL_ANSWER, None, None
    try:
        content = llm_response.content if isinstance(llm_response.content, str) else llm_response.text
        deserialized_content = json.loads(content)
        # content_status = deserialized_content.get('status')
        # if content_status in constant.LLM_RESPONCED_WITH_ERROR_OPTIONS:
        #     logger.error(f"LLM returned status {content_status}: {deserialized_content.get('message')}")
        #     return thought, action, action_input
        # thought = deserialized_content["thought"]
        # action = deserialized_content["action"]
        # action_input = deserialized_content["action_input"]
    except Exception as e:
        logger.exception(e)
    
    finally:
        return thought, action, action_input

1