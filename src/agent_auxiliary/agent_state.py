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
    tool_name: str = Field(default="", description="Name of the tool to call when action_type is \"act\"")
    tool_kwargs: dict = Field(default_factory=dict, description="Keyword arguments for the tool call")
    tool_observation: str = Field(default="", description="Result returned by the last tool call")
    tool_call_id: str = Field(default="", description="Unique identifier for tool call")
    answer: str = Field(default="", description="Final answer")
    truncated: bool = Field(default=False, description="Whether the answer was cut short by the iteration cap")
    iterations: int = Field(default=0, description="Number of iterations")
    max_iterations: int = Field(default=10, description="Maximum iterations allowed")

    class Config:
        arbitrary_types_allowed = True



