"""
Lambda streaming handler for the personal AI assistant chat endpoint.

Invoked via a Lambda Function URL configured with InvokeMode: RESPONSE_STREAM.
The ReAct agent processes the full query (reason → act → finalize) and the
final answer is forwarded to the client as a single Server-Sent Event (SSE).

Frontend consumes the stream using the fetch() streaming API (not EventSource,
because Lambda Function URLs require POST):

    const res = await fetch(LAMBDA_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
    });
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        // parse SSE lines: "data: {...}\\n\\n"
    }
"""
import asyncio
import json
from awslambdaric.bootstrap import streamify
from dotenv import load_dotenv
from src.agent_auxiliary.agent_factory import AgentPattern, create_agent
from src.agents.react_agent import ReactAgent
import src.resources.constants as constant
from src.service_utils.logger import get_logger

load_dotenv()


class ChatHandler:
    """
    Owns a warm ReactAgent instance and handles Lambda streaming invocations.
    Created once per Lambda container — reused on warm invocations.
    """

    def __init__(self) -> None:
        self._agent: ReactAgent = create_agent(
            AgentPattern.REACT,
            model=constant.DEFAULT_MODEL,
            temperature=constant.DEFAULT_TEMPERATURE,
        )
        self._logger = get_logger()

    def handle(self, event: dict, context: object, response_stream) -> None:
        """
        Core Lambda handler. Streams intermediate agent state events and the final
        answer to the client as SSE frames.

        Frame shapes:
          data: {"type": "reasoning", "thought": "...", "iteration": N}
          data: {"type": "acting",    "tool": "...", "input": "..."}
          data: {"type": "answer",    "token": "..."}
          data: [DONE]
        """
        try:
            query = self._parse_query(event)
            if not query:
                self._write_sse(response_stream, b'data: {"error": "Missing or empty query"}\n\n')
                self._write_sse(response_stream, b"data: [DONE]\n\n")
                return

            asyncio.run(self._run_stream(query, response_stream))

        except Exception as e:
            self._logger.error("Streaming error: %s", e)
            self._write_sse(response_stream, b'data: {"error": "Internal server error"}\n\n')
            self._write_sse(response_stream, b"data: [DONE]\n\n")

    async def _run_stream(self, query: str, response_stream) -> None:
        """Drive astream_events and forward each event as an SSE frame."""
        async for event in self._agent.astream_events(query):
            payload = json.dumps(event)
            self._write_sse(response_stream, f"data: {payload}\n\n".encode("utf-8"))
        self._write_sse(response_stream, b"data: [DONE]\n\n")

    def _parse_query(self, event: dict) -> str:
        """Extract and strip the query string from the Lambda event body."""
        body = json.loads(event.get("body") or "{}")
        return body.get("query", "").strip()

    def _write_sse(self, stream, payload: bytes) -> None:
        """Write a single SSE frame to the response stream."""
        stream.write(payload)


# Created once per Lambda cold start — reused on warm invocations.
_chat_handler = ChatHandler()


def _streaming_handler(event: dict, context: object, response_stream) -> None:
    _chat_handler.handle(event, context, response_stream)


# streamify wraps the handler so the Lambda runtime uses RESPONSE_STREAM mode.
handler = streamify(_streaming_handler)


if __name__ == "__main__":
    import io

    class _MockStream:
        def write(self, data: bytes) -> None:
            print(data.decode("utf-8"), end="")

    test_query = "Hello! Who are you and what can you help me with?"
    mock_event = {"body": json.dumps({"query": test_query})}
    print(f"Query: {test_query}\nResponse:\n")
    _chat_handler.handle(mock_event, None, _MockStream())
