"""
FastAPI handler for the personal AI assistant chat endpoint, plus a small
direct endpoint for the "Hire me" meeting-request form (POST /schedule-meeting).

The managed Python Lambda runtime (awslambdaric) has no native response-streaming
support — only Node.js does. So this Lambda is deployed as an ordinary ASGI app
(see run.sh) behind the AWS Lambda Web Adapter, which proxies streamed HTTP
responses through the Lambda Runtime API. The Function URL is configured with
InvokeMode: RESPONSE_STREAM and the adapter with AWS_LWA_INVOKE_MODE=response_stream
(see template.yaml) so tokens reach the browser as they're produced.

The ReAct agent processes the full query (reason -> act -> finalize). Reasoning calls are
streamed token-by-token from the LLM: responses starting with the "act:" sentinel are tool
calls (buffered internally, surfaced as one short "acting" event), everything else is the
final answer and is forwarded live as "answer" token events over Server-Sent Events (SSE).

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
from datetime import datetime
from typing import AsyncGenerator, Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from src.agent_auxiliary.agent_factory import AgentPattern, create_agent
from src.agents.react_agent import ReactAgent
from src.agent_tools.tools import MeetingScheduledStatus, ToolCallback
from src.service_utils import rate_limiter
import src.resources.constants as constant
from src.service_utils.logger import get_logger
import uvicorn

load_dotenv()

app = FastAPI()
_logger = get_logger()

# Handles CORS (including OPTIONS preflight) at the app level rather than relying
# solely on the Lambda Function URL's Cors config, since this image also runs
# outside Lambda (ECS/EKS/Fargate/local), where no such config exists.
app.add_middleware(
    CORSMiddleware,
    allow_origins=constant.ALLOWED_ORIGINS,
    allow_methods=["POST"],
    allow_headers=["content-type"],
    max_age=86400,
)

# Created once per Lambda container (or process, when run locally) — reused on warm invocations.
_agent: ReactAgent = create_agent(
    AgentPattern.REACT,
    model=constant.DEFAULT_MODEL,
    temperature=constant.DEFAULT_TEMPERATURE,
)


class ScheduleMeetingRequest(BaseModel):
    """Body for the "Hire me" modal's direct meeting-request form."""
    attendee_email: str
    scheduled_at: datetime
    description: str


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
      data: {"type": "acting", "tool": "..."}     (once per reasoning step that calls tool(s);
                                                     "tool" joins every name with " -> " when
                                                     more than one was chosen)
      data: {"type": "answer", "token": "..."}    (streamed token-by-token)
      data: [DONE]
    """
    body = await request.json()
    query = (body.get("query") or "").strip()
    caller_ip = request.headers.get("x-client-ip")
    return StreamingResponse(_stream_response(query, caller_ip), media_type="text/event-stream")


@app.post("/wake-up")
async def wake_up() -> JSONResponse:
    """
    Lightweight no-op hit by the frontend when the user opens the chat, so
    this container cold-starts (imports, agent/model client construction)
    ahead of the first real chat message instead of during it.

    landing-api-worker throttles this to one call per caller per 2h (Workers
    KV) before it ever reaches here — every request that does reach this
    handler should be treated as a genuine warm-up, so no rate limiting is
    duplicated on this side.
    """
    return JSONResponse({"message": "warm up started"})


@app.post("/schedule-meeting")
async def schedule_meeting(payload: ScheduleMeetingRequest, request: Request) -> Response:
    """
    Handle the "Hire me" modal's form directly — bypasses the LLM agent entirely
    and calls `ToolCallback.schedule_meeting` with the submitted fields, since the
    modal already collects everything the tool needs as structured input.

    Enforces the shared 24h "one meeting per user" cooldown (see
    `src.service_utils.rate_limiter`) — identity is `attendee_email`, falling back to
    the caller's IP (`x-client-ip`, forwarded by landing-api-worker) when absent. The
    same check also guards the agent's schedule_meeting tool call from "/".
    """
    identity = rate_limiter.resolve_identity(payload.attendee_email, request.headers.get("x-client-ip"))
    if rate_limiter.is_blocked(identity):
        return JSONResponse(
            {"error": "You've already scheduled a meeting recently. Please try again in 24 hours."},
            status_code=429,
            headers={"Retry-After": str(constant.SCHEDULE_MEETING_BLOCK_TTL_SECONDS)},
        )

    status = ToolCallback.schedule_meeting(
        title=constant.HIRE_MEETING_TITLE_TEMPLATE.format(email=payload.attendee_email),
        scheduled_at=payload.scheduled_at,
        description=payload.description,
        attendee_email=payload.attendee_email,
    )
    if status != MeetingScheduledStatus.NOT_SCHEDULED:
        rate_limiter.mark_blocked(identity)
    return JSONResponse({"status": status})


async def _stream_response(query: str, caller_ip: Optional[str] = None) -> AsyncGenerator[str, None]:
    """Drive astream_events and yield each event as an SSE frame."""
    if not query:
        yield 'data: {"error": "Missing or empty query"}\n\n'
        yield "data: [DONE]\n\n"
        return

    try:
        async for event in _agent.astream_events(query, caller_ip=caller_ip):
            yield f"data: {json.dumps(event)}\n\n"
    except Exception as exc:
        _logger.error("Streaming error: %s", exc)
        yield 'data: {"error": "Internal server error"}\n\n'

    yield "data: [DONE]\n\n"


if __name__ == "__main__":


    uvicorn.run(app, host="0.0.0.0", port=8000)
