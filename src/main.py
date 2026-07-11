"""
Lambda streaming handler for the personal AI assistant chat endpoint.

Invoked via a Lambda Function URL configured with InvokeMode: RESPONSE_STREAM.
Tokens from Gemini are forwarded to the client as Server-Sent Events (SSE).

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
import json
from awslambdaric.bootstrap import streamify
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
import src.resources.constants as constant
from src.service_utils.logger import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger()

# Initialized once per Lambda container — reused on warm invocations
_llm = ChatGoogleGenerativeAI(
    model=constant.DEFAULT_MODEL,
    temperature=constant.DEFAULT_TEMPERATURE,
)


def _build_messages(query: str) -> list:
    return [
        SystemMessage(content=constant.SYSTEM_PROMPT),
        HumanMessage(content=query),
    ]


def _streaming_handler(event: dict, context: object, response_stream) -> None:
    """
    Core Lambda handler. Writes SSE-formatted chunks to response_stream.

    Each chunk: b"data: {json}\\n\\n"
    Final chunk: b"data: [DONE]\\n\\n"
    """
    try:
        body = json.loads(event.get("body") or "{}")
        query: str = body.get("query", "").strip()

        if not query:
            response_stream.write(b'data: {"error": "Missing or empty query"}\n\n')
            response_stream.write(b"data: [DONE]\n\n")
            return

        for chunk in _llm.stream(_build_messages(query)):
            if chunk.content:
                payload = json.dumps({"token": chunk.content})
                response_stream.write(f"data: {payload}\n\n".encode("utf-8"))

        response_stream.write(b"data: [DONE]\n\n")

    except Exception as e:
        logger.error("Streaming error: %s", e)
        response_stream.write(b'data: {"error": "Internal server error"}\n\n')
        response_stream.write(b"data: [DONE]\n\n")


# streamify wraps the handler so the Lambda runtime uses RESPONSE_STREAM mode
handler = streamify(_streaming_handler)


if __name__ == "__main__":
    # Local smoke test — prints streamed tokens to stdout (no Lambda runtime needed)
    load_dotenv()
    test_query = "Hello! Who are you and what can you help me with?"
    llm = ChatGoogleGenerativeAI(model=constant.DEFAULT_MODEL, temperature=constant.DEFAULT_TEMPERATURE)
    print(f"Query: {test_query}\nResponse: ", end="", flush=True)
    for chunk in llm.stream(_build_messages(test_query)):
        if chunk.content:
            print(chunk.content, end="", flush=True)
    print()
