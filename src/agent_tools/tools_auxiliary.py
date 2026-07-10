from typing import List, Callable, Tuple
from langchain_core.tools import Tool
from src.agent_tools.http_tools import http_request
from src.agent_tools.browser_tools import browser_navigate, analyze_network_logs, extract_page_structure
from src.service_utils.logger import get_logger

AVAILABLE_CALLBACKS = [
    http_request, 
    analyze_network_logs, 
    browser_navigate, 
    extract_page_structure
]

logger = get_logger()

def extract_and_parse_doc(callback: Callable) -> Tuple[str, str]:
    callback_doc = callback.__doc__
    callback_name = callback.__name__
    if callback_doc is None:
        raise ValueError(f"Tool callback ``{callback_name}`` doesn't have description for agent")

    return callback_name, callback_doc


def get_tools() -> List[Tool]:
    tools = []
    for callback in AVAILABLE_CALLBACKS:
        name, description = extract_and_parse_doc(callback)
        tools.append(
            Tool(
                name=name,
                func=callback,
                description=description
            )
        )

    return tools
