import inspect
from typing import List, Callable
from langchain_core.tools import Tool
from src.service_utils.logger import get_logger
from src.agent_tools.tools import ToolCallback

logger = get_logger()

def extract_and_parse_doc(name: str, callback: Callable) -> str:
    callback_doc = callback.__doc__
    if callback_doc is None:
        raise ValueError(f"Tool callback ``{name}`` doesn't have description for agent")

    return callback_doc


def get_tools() -> List[Tool]:
    tools = []
    for name, method in inspect.getmembers(ToolCallback):
        if not isinstance(inspect.getattr_static(ToolCallback, name), staticmethod):
            continue
        description = extract_and_parse_doc(name, method)
        tools.append(
            Tool(
                name=name,
                func=method,
                description=description
            )
        )

    return tools


