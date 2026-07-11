from typing import Any, AsyncGenerator
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.service_utils.logger import get_logger
from src.agent_auxiliary.agent_state import AgentState
from src.agent_auxiliary.utils import get_initial_state, parse_llm_response
from src.agent_tools.tools_auxiliary import get_tools
import src.resources.constants as constant
from dotenv import load_dotenv
import uuid


class ReactAgent:
    def __init__(self, model: str = "gemini-3-flash-preview", temperature: float = 0.7):
        load_dotenv()
        self._llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature
        )
        self._logger = get_logger()
        self._tools = get_tools()
        self._tool_dict = {tool.name: tool for tool in self._tools}
        self._graph = self._build_graph()

    def bind(self, temperature=None, model=None):
        params = dict[Any, Any]()
        if temperature:
            params["temperature"] = temperature
        if model:
            params["model"] = model

        if not(temperature or model):
            self._logger.error("Invoking method with both None params")

        self._llm.bind(**params)
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph for ReAct pattern."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node(constant.REASON, self._reason_node)
        workflow.add_node(constant.ACT, self._act_node)
        workflow.add_node(constant.FINALIZE, self._finalize_node)
        
        # Add edges
        workflow.set_entry_point(constant.REASON)
        workflow.add_conditional_edges(
            constant.REASON,
            self._should_continue,
            {
                constant.CONTINUE: constant.ACT,
                constant.END: constant.FINALIZE
            }
        )
        workflow.add_edge(constant.ACT, constant.REASON)
        workflow.add_edge(constant.FINALIZE, END)
        
        return workflow.compile()
    
    async def _reason_node(self, state: AgentState) -> dict[str, Any]:
        """
        Reasoning node: decides what action to take next.
        """
        # messages_to_merge, state_messages = [], []
        if state.iterations == 0:
            if not state.input:
                raise ValueError("state.input cannot be empty")
            # Build the reasoning prompt
            tool_descriptions = "\n".join([
                f"- {tool.name}: {tool.description}"
                for tool in self._tools
            ])
            system_prompt = constant.SYSTEM_PROMPT + "\n\nAvailable tools:\n" + tool_descriptions
            state_messages = [SystemMessage(content=system_prompt), HumanMessage(content=state.input)]
            messages_to_merge = state_messages

        else:
            messages_to_merge = []
            state_messages = state.messages
            if state.observation:
                tool_msg = ToolMessage(
                    content=state.observation,
                    tool_call_id=state.tool_call_id
                )
                human_message = HumanMessage(content=constant.OBSERVER_CONTENT)
                state_messages.append(tool_msg)
                state_messages.append(human_message)
                messages_to_merge.append(tool_msg)
                messages_to_merge.append(human_message)

        response = await self._llm.ainvoke(state_messages)
        messages_to_merge.append(response)

        thought, action, action_input = parse_llm_response(response, self._logger)
        return {
            "messages": messages_to_merge,
            "thought": thought,
            "action": action,
            "action_input": action_input,
            "iterations": state.iterations + 1
        }
    
    async def _act_node(self, state: AgentState) -> dict[str, Any]:
        """
        Action node: executes the chosen action.
        """
        tool_call_id = str(uuid.uuid4())
        
        if state.action in self._tool_dict:
            tool = self._tool_dict[state.action]
            try:
                observation = tool.func(state.action_input)
            except Exception as e:
                observation = f"Error executing tool: {str(e)}"
        else:
            observation = f"Unknown tool: {state.action}"
        
        return {
            "observation": observation,
            "tool_call_id": tool_call_id
        }
    
    def _should_continue(self, state: AgentState) -> str:
        """
        Determines whether to continue reasoning or finalize.
        """
        if state.action == constant.FINAL_ANSWER or state.iterations >= state.max_iterations:
            return constant.END
        return constant.CONTINUE
    
    async def _finalize_node(self, state: AgentState) -> dict[str, Any]:
        """
        Finalization node: prepares the final answer.
        """
        if state.iterations >= state.max_iterations:
            answer = f"Maximum iterations reached. Last thought: {state.thought}"
        else:
            answer = state.action_input
        
        return {"answer": answer}
    
    async def run(self, query: str, max_iterations: int = 10) -> str:
        """Run the ReAct agent on a query and return the final answer."""
        initial_state = get_initial_state(query=query, max_iterations=max_iterations)
        result = await self._graph.ainvoke(initial_state)
        return result["answer"]

    async def astream_events(
        self, query: str, max_iterations: int = 10
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream intermediate agent state events as the graph executes.

        Yields one dict per node completion:
          - {type: "reasoning", thought: str, iteration: int}
          - {type: "acting",   tool: str, input: str}
          - {type: "answer",   token: str}
        """
        initial_state = get_initial_state(query=query, max_iterations=max_iterations)
        last_action: str = ""
        last_action_input: str = ""

        async for chunk in self._graph.astream(initial_state):
            node_name, update = next(iter(chunk.items()))

            if node_name == constant.REASON:
                last_action = update.get("action") or ""
                last_action_input = update.get("action_input") or ""
                yield {
                    "type": "reasoning",
                    "thought": update.get("thought", ""),
                    "iteration": update.get("iterations", 0),
                }
            elif node_name == constant.ACT:
                yield {
                    "type": "acting",
                    "tool": last_action,
                    "input": last_action_input,
                }
            elif node_name == constant.FINALIZE:
                yield {"type": "answer", "token": update.get("answer", "")}

