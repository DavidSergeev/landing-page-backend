import inspect
from typing import List, Callable
from langchain_core.tools import StructuredTool
from src.service_utils.logger import get_logger
from src.agent_tools.tools import ToolCallback

logger = get_logger()

def extract_and_parse_doc(name: str, callback: Callable) -> str:
    callback_doc = callback.__doc__
    if callback_doc is None:
        raise ValueError(f"Tool callback ``{name}`` doesn't have description for agent")

    return callback_doc


def get_tools() -> List[StructuredTool]:
    """
    Build tools from `ToolCallback`'s static methods using `StructuredTool`, whose
    per-argument JSON schema is inferred from each method's type-hinted signature. This
    is required for tool binding: the model relies on that schema (rather than a
    hand-written description) to know which arguments each tool expects.
    """
    tools = []
    for name, method in inspect.getmembers(ToolCallback):
        if not isinstance(inspect.getattr_static(ToolCallback, name), staticmethod):
            continue
        description = extract_and_parse_doc(name, method)
        tools.append(
            StructuredTool.from_function(
                name=name,
                func=method,
                description=description
            )
        )

    return tools


