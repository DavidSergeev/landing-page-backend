"""
FastAPI streaming handler for the personal AI assistant chat endpoint.

The managed Python Lambda runtime (awslambdaric) has no native response-streaming
support — only Node.js does. So this Lambda is deployed as an ordinary ASGI app
(see run.sh) behind the AWS Lambda Web Adapter, which proxies streamed HTTP
responses through the Lambda Runtime API. The Function URL is configured with
InvokeMode: RESPONSE_STREAM and the adapter with AWS_LWA_INVOKE_MODE=response_stream
(see template.yaml) so tokens reach the browser as they're produced.

The ReAct agent processes the full query (reason -> act -> finalize) and each
intermediate/final event is forwarded to the client as a Server-Sent Event (SSE).

Frontend consumes the stream using the fetch() streaming API (not EventSource,
because Lambda Function URLs require POST):

    const res = await fetch(CHAT_URL, {
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
import json
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from src.agent_auxiliary.agent_factory import AgentPattern, create_agent
from src.agents.react_agent import ReactAgent
import src.resources.constants as constant
from src.service_utils.logger import get_logger

load_dotenv()

app = FastAPI()
_logger = get_logger()

# Created once per Lambda container (or process, when run locally) — reused on warm invocations.
_agent: ReactAgent = create_agent(
    AgentPattern.REACT,
    model=constant.DEFAULT_MODEL,
    temperature=constant.DEFAULT_TEMPERATURE,
)


@app.get("/")
async def health() -> dict:
    """Readiness probe polled by the Lambda Web Adapter during cold start."""
    return {"status": "ok"}


@app.post("/")
async def chat(request: Request) -> StreamingResponse:
    """
    Stream intermediate agent state events and the final answer to the client
    as SSE frames.

    Frame shapes:
      data: {"type": "reasoning", "thought": "...", "iteration": N}
      data: {"type": "acting",    "tool": "...", "input": "..."}
      data: {"type": "answer",    "token": "..."}
      data: [DONE]
    """
    body = await request.json()
    query = (body.get("query") or "").strip()
    return StreamingResponse(_stream_response(query), media_type="text/event-stream")


async def _stream_response(query: str) -> AsyncGenerator[str, None]:
    """Drive astream_events and yield each event as an SSE frame."""
    if not query:
        yield 'data: {"error": "Missing or empty query"}\n\n'
        yield "data: [DONE]\n\n"
        return

    try:
        async for event in _agent.astream_events(query):
            yield f"data: {json.dumps(event)}\n\n"
    except Exception as exc:
        _logger.error("Streaming error: %s", exc)
        yield 'data: {"error": "Internal server error"}\n\n'

    yield "data: [DONE]\n\n"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
