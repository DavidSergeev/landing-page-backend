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
    thought: str = Field(default="", description="The current thought or reasoning")
    action: str = Field(default="", description="Action to take (tool name)")
    action_input: str = Field(default="", description="Input for the action")
    observation: str = Field(default="", description="Result from the action")
    tool_call_id: str = Field(default="", description="Unique identifier for tool call")
    answer: str = Field(default="", description="Final answer")
    iterations: int = Field(default=0, description="Number of iterations")
    max_iterations: int = Field(default=10, description="Maximum iterations allowed")

    class Config:
        arbitrary_types_allowed = True



