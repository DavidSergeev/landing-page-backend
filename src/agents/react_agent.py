from typing import Any, AsyncGenerator
import os
import uuid
import boto3
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.service_utils.logger import get_logger
from src.agent_auxiliary.agent_state import AgentState
from src.agent_auxiliary.utils import get_initial_state, parse_llm_response
from src.agent_tools.tools_auxiliary import get_tools
from src.db.config_repository import get_system_prompt
import src.resources.constants as constant
from dotenv import load_dotenv


class ReactAgent:
    def __init__(self, model: str = "gemini-3-flash-preview", temperature: float = 0.7):
        load_dotenv()
        self._logger = get_logger()
        self._load_google_api_key()
        self._llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature
        )
        self._tools = get_tools()
        self._tool_dict = {tool.name: tool for tool in self._tools}
        self._system_prompt = self._load_system_prompt()
        self._graph = self._build_graph()

    def _load_system_prompt(self) -> str:
        """Load system prompt from DynamoDB by SYS_PROMPT_VERSION env var; falls back to constant."""
        raw = os.environ.get("SYS_PROMPT_VERSION", "1")
        if raw.isdigit():
            version = int(raw)
            prompt = get_system_prompt(version)
            if prompt:
                self._logger.info("Loaded system prompt version %d from DynamoDB", version)
                return prompt
            self._logger.warning(
                "System prompt v%d not found in DynamoDB, using built-in fallback", version
            )
        else:
            self._logger.warning("SYS_PROMPT_VERSION not set or invalid, using built-in fallback")
        return constant.DEFAULT_SYSTEM_PROMPT

    def _load_google_api_key(self) -> None:
        """Load the Google API key from SSM if GOOGLE_API_KEY is not already set."""
        if os.environ.get("GOOGLE_API_KEY"):
            return

        parameter_path = os.environ.get("GOOGLE_API_KEY_PATH", "").strip()
        if not parameter_path:
            self._logger.warning("GOOGLE_API_KEY_PATH is not set; using existing environment value if any")
            return

        try:
            client = boto3.client("ssm")
            response = client.get_parameter(Name=parameter_path, WithDecryption=True)
            secret = response["Parameter"]["Value"]
            os.environ["GOOGLE_API_KEY"] = secret
            self._logger.info("Loaded Google API key from SSM path %s", parameter_path)
        except Exception as exc:
            self._logger.error(
                "Failed to load Google API key from SSM (%s): %s",
                parameter_path,
                exc,
            )

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
            system_prompt = self._system_prompt + "\n\nAvailable tools:\n" + tool_descriptions
            state_messages = [SystemMessage(content=system_prompt), HumanMessage(content=state.input)]
            messages_to_merge = state_messages

        else:
            messages_to_merge = []
            state_messages = state.messages
            if state.tool_observation:
                tool_msg = ToolMessage(
                    content=state.tool_observation,
                    tool_call_id=state.tool_call_id
                )
                human_message = HumanMessage(content=constant.OBSERVER_CONTENT)
                state_messages.append(tool_msg)
                state_messages.append(human_message)
                messages_to_merge.append(tool_msg)
                messages_to_merge.append(human_message)

        response = await self._llm.ainvoke(state_messages)
        messages_to_merge.append(response)

        thoughts, action_type, tool_name, tool_kwargs = parse_llm_response(response, self._logger)
        return {
            "messages": messages_to_merge,
            "thoughts": thoughts,
            "action_type": action_type,
            "tool_name": tool_name or "",
            "tool_kwargs": tool_kwargs,
            "iterations": state.iterations + 1
        }
    
    async def _act_node(self, state: AgentState) -> dict[str, Any]:
        """
        Action node: executes the chosen action.
        """
        tool_call_id = str(uuid.uuid4())
        
        if state.tool_name in self._tool_dict:
            tool = self._tool_dict[state.tool_name]
            try:
                tool_observation = tool.func(**state.tool_kwargs)
            except Exception as e:
                tool_observation = f"Error executing tool: {str(e)}"
        else:
            tool_observation = f"Unknown tool: {state.tool_name}"
        
        return {
            "tool_observation": tool_observation,
            "tool_call_id": tool_call_id
        }
    
    def _should_continue(self, state: AgentState) -> str:
        """
        Determines whether to continue reasoning or finalize.
        """
        if state.action_type == constant.ACT and state.iterations < state.max_iterations:
            return constant.CONTINUE
        return constant.END
    
    async def _finalize_node(self, state: AgentState) -> dict[str, Any]:
        """
        Finalization node: prepares the final answer.
        """
        if state.iterations >= state.max_iterations:
            answer = f"Maximum iterations reached. Last thought: {state.thoughts}"
        else:
            answer = state.thoughts
            if answer.startswith(constant.FINAL_ANSWER_PREFIX):
                answer = answer[len(constant.FINAL_ANSWER_PREFIX):]
        
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
          - {type: "acting",   tool: str, input: dict}
          - {type: "answer",   token: str}
        """
        initial_state = get_initial_state(query=query, max_iterations=max_iterations)
        last_tool_name: str = ""
        last_tool_kwargs: dict[str, Any] = {}

        async for chunk in self._graph.astream(initial_state):
            node_name, update = next(iter(chunk.items()))

            if node_name == constant.REASON:
                last_tool_name = update.get("tool_name") or ""
                last_tool_kwargs = update.get("tool_kwargs") or {}
                yield {
                    "type": "reasoning",
                    "thought": update.get("thoughts", ""),
                    "iteration": update.get("iterations", 0),
                }
            elif node_name == constant.ACT:
                yield {
                    "type": "acting",
                    "tool": last_tool_name,
                    "input": last_tool_kwargs,
                }
            elif node_name == constant.FINALIZE:
                yield {"type": "answer", "token": update.get("answer", "")}

