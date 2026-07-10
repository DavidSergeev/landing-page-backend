import sys
import asyncio
from src.agents.react_agent import ReactAgent

def main():
    exit_code = 0

    react_agent = ReactAgent()

    result = asyncio.run(react_agent.run(
        "Calculate (10 * 5) + (20 * 3) and tell me the result. "
        "Break it down into steps: first calculate 10 * 5, then 20 * 3, then add them."
    ))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())