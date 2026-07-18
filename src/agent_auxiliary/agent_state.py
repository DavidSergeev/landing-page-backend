"""
State definitions for LangGraph-based agents.
"""
from typing import Annotated, Sequence
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
import operator


class AgentState(BaseModel):
    """Base state for all agent patterns."""
    input: str = Field(default="", description="The input query from the user")
    messages: Annotated[Sequence[BaseMessage], operator.add] = Field(default_factory=list, description="History of messages in the conversation")
    thoughts: str = Field(default="", description="The current thought or reasoning")
    action_type: str = Field(default="", description="Whether the LLM chose to \"reason\" or \"act\"")
    tool_names: list[str] = Field(default_factory=list, description="Names of the tools to call when action_type is \"act\"")
    tool_kwargs_list: list[dict] = Field(default_factory=list, description="Keyword arguments for each tool call, aligned with tool_names")
    tool_observations: list[str] = Field(default_factory=list, description="Results returned by the last batch of tool calls, aligned with tool_call_ids")
    tool_call_ids: list[str] = Field(default_factory=list, description="Unique identifiers for each tool call, aligned with tool_names/tool_kwargs_list")
    answer: str = Field(default="", description="Final answer")
    truncated: bool = Field(default=False, description="Whether the answer was cut short by the iteration cap")
    iterations: int = Field(default=0, description="Number of iterations")
    max_iterations: int = Field(default=10, description="Maximum iterations allowed")

    class Config:
        arbitrary_types_allowed = True



