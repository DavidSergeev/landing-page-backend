from dotenv import load_dotenv
from src.agent_auxiliary.agent_factory import AgentPattern, create_agent
from src.agents.react_agent import ReactAgent
import src.resources.constants as constant
from src.service_utils.logger import get_logger
import asyncio
load_dotenv()

logger = get_logger()


async def stream_query(agent: ReactAgent, query: str) -> None:
    """Stream a single query, printing every event plus the assembled final answer."""
    print(f"\n=== Query: {query!r} ===")
    answer_tokens: list[str] = []
    async for event in agent.astream_events(query, max_iterations=10):
        print(event)
        if event.get("type") == "answer":
            answer_tokens.append(event["token"])
        
    print(f"--- Final answer ---\n{''.join(answer_tokens)}")


async def main():
    # Created once per Lambda container (or process, when run locally) — reused on warm invocations.
    agent: ReactAgent = create_agent(
        AgentPattern.REACT,
        model=constant.DEFAULT_MODEL,
        temperature=constant.DEFAULT_TEMPERATURE,
    )

    # Simple query: no tool call expected, exercises the plain streamed-answer path.
    #await stream_query(agent, "Hi! Give short explanation about quantum mechanics.")

    # Query expected to trigger the get_user_info tool, exercising the "acting" event
    # and the act/final-answer detection on the follow-up reasoning call.
    await stream_query(agent, "Tell me about David's background and experience.")


if __name__ == "__main__":
    asyncio.run(main())
