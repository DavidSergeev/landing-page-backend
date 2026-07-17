from dotenv import load_dotenv
from src.agent_auxiliary.agent_factory import AgentPattern, create_agent
from src.agents.react_agent import ReactAgent
import src.resources.constants as constant
from src.service_utils.logger import get_logger
import asyncio
load_dotenv()

async def main():
    # Created once per Lambda container (or process, when run locally) — reused on warm invocations.
    agent: ReactAgent = create_agent(
        AgentPattern.REACT,
        model=constant.DEFAULT_MODEL,
        temperature=constant.DEFAULT_TEMPERATURE,
    )

    async for event in agent.astream_events("Hi!", max_iterations=10):
        print(event)
        if event.get("type") == "answer":
            break

if __name__ == "__main__":
    asyncio.run(main())