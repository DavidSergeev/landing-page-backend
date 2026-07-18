from typing import Any, AsyncGenerator, Optional
import os
import uuid
import boto3
from langgraph.graph import StateGraph, END
from langgraph.types import StreamWriter
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.service_utils.logger import get_logger
from src.agent_auxiliary.agent_state import AgentState
from src.agent_auxiliary.utils import extract_text_content, get_initial_state
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
        self._llm_with_tools = self._llm.bind_tools(self._tools)
        self._system_prompt = self._load_system_prompt()
        self._graph = self._build_graph()

    def _load_system_prompt(self) -> str:
        """Load system prompt from DynamoDB by SYS_PROMPT_VERSION env var; falls back to constant."""
        raw = os.environ.get("SYS_PROMPT_VERSION", "")
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
    
    async def _reason_node(self, state: AgentState, writer: StreamWriter) -> dict[str, Any]:
        """
        Reasoning node: streams the LLM's response and decides what to do next.

        Tool-call decisions are resolved natively via `self._llm_with_tools` (tool binding)
        instead of being parsed from free-form text. The call is always streamed via
        `astream`; tokens are forwarded live to the SSE client via `writer` as an
        `{"type": "answer", "token": ...}` custom event as soon as the response is
        classified as a final answer (i.e. the model isn't streaming a tool call), while a
        tool-call response stays buffered and is only exposed via `AIMessage.tool_calls`.
        """
        if state.iterations == 0:
            if not state.input:
                raise ValueError("state.input cannot be empty")
            state_messages = [SystemMessage(content=self._system_prompt), HumanMessage(content=state.input)]
            messages_to_merge = state_messages

        else:
            messages_to_merge = []
            state_messages = state.messages
            if state.tool_observations:
                tool_msgs = [
                    ToolMessage(content=observation, tool_call_id=tool_call_id)
                    for tool_call_id, observation in zip(state.tool_call_ids, state.tool_observations)
                ]
                human_message = HumanMessage(content=constant.OBSERVER_CONTENT)
                state_messages.extend(tool_msgs)
                state_messages.append(human_message)
                messages_to_merge.extend(tool_msgs)
                messages_to_merge.append(human_message)

        ai_message = await self._stream_response(state_messages, writer)
        messages_to_merge.append(ai_message)

        tool_calls = ai_message.tool_calls
        return {
            "messages": messages_to_merge,
            "thoughts": extract_text_content(ai_message.content),
            "action_type": constant.ACT if tool_calls else constant.REASON,
            "tool_names": [call["name"] for call in tool_calls],
            "tool_kwargs_list": [call.get("args") or {} for call in tool_calls],
            "tool_call_ids": [call.get("id") or str(uuid.uuid4()) for call in tool_calls],
            "iterations": state.iterations + 1
        }

    async def _stream_response(self, messages: list[BaseMessage], writer: StreamWriter) -> AIMessage:
        """
        Stream the LLM's response, forwarding text tokens live only once the response is
        classified as a final answer (i.e. the model isn't streaming a tool call). Returns
        the full accumulated `AIMessage`, tool calls included.
        """
        full_message: Optional[AIMessageChunk] = None
        is_act: Optional[bool] = None

        async for chunk in self._llm_with_tools.astream(messages):
            full_message = chunk if full_message is None else full_message + chunk
            if is_act:
                continue
            if chunk.tool_call_chunks:
                is_act = True
                writer(
                    {"type": "act", "tools_invocation": [tool_item['name'] for tool_item in chunk.tool_call_chunks]})
                continue
            text = extract_text_content(chunk.content)
            if text:
                is_act = False
                writer({"type": "answer", "token": text})

        return full_message
    
    async def _act_node(self, state: AgentState) -> dict[str, Any]:
        """
        Action node: executes every tool call chosen in the last reasoning step (the model
        may request more than one per turn). `state.tool_call_ids` is already set by
        `_reason_node` from the model's own tool calls, so each resulting observation stays
        aligned by index and can be correlated with its originating call via `ToolMessage`.
        """
        tool_observations = []
        for tool_name, tool_kwargs in zip(state.tool_names, state.tool_kwargs_list):
            if tool_name not in self._tool_dict:
                tool_observations.append(f"Unknown tool: {tool_name}")
                continue
            try:
                tool_observations.append(self._tool_dict[tool_name].func(**tool_kwargs))
            except Exception as e:
                tool_observations.append(f"Error executing tool: {str(e)}")

        return {"tool_observations": tool_observations}
    
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

        `truncated` is only True when the iteration cap was hit while the model still
        wanted to act — in that case there is no answer text yet (nothing was streamed),
        so this message must be sent as a one-off, non-streamed event. Otherwise the
        answer was already streamed token-by-token from `_reason_node`.
        """
        truncated = state.action_type == constant.ACT and state.iterations >= state.max_iterations
        if truncated:
            tools = ", ".join(state.tool_names)
            answer = f"Maximum iterations reached while attempting to use tool(s): {tools}."
        else:
            answer = state.thoughts

        return {"answer": answer, "truncated": truncated}
    
    async def run(self, query: str, max_iterations: int = 10) -> str:
        """Run the ReAct agent on a query and return the final answer."""
        initial_state = get_initial_state(query=query, max_iterations=max_iterations)
        result = await self._graph.ainvoke(initial_state)
        return result["answer"]

    async def astream_events(
        self, query: str, max_iterations: int = 10
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream agent events as the graph executes.

        Yields:
          - {type: "acting",  tool: str, input: dict}   once a tool call is decided
          - {type: "answer",  token: str}                streamed token-by-token as the final
            answer is generated; also emitted once, non-streamed, if the iteration cap is
            hit while a tool call was still pending
        """
        initial_state = get_initial_state(query=query, max_iterations=max_iterations)
        last_tool_names: list[str] = []
        last_tool_kwargs_list: list[dict[str, Any]] = []

        async for stream_mode, payload in self._graph.astream(
            initial_state, stream_mode=["updates", "custom"]
        ):
            if stream_mode == "custom":
                yield payload
                continue

            node_name, update = next(iter(payload.items()))
            if node_name == constant.REASON:
                last_tool_names = update.get("tool_names") or []
                last_tool_kwargs_list = update.get("tool_kwargs_list") or []
            elif node_name == constant.ACT:
                for tool_name, tool_kwargs in zip(last_tool_names, last_tool_kwargs_list):
                    yield {"type": "acting", "tool": tool_name, "input": tool_kwargs}
            elif node_name == constant.FINALIZE and update.get("truncated"):
                yield {"type": "answer", "token": update.get("answer", "")}

