from enum import Enum
from typing import Union
from src.agents.react_agent import ReactAgent


class AgentPattern(Enum):
    """
    Enumeration of available agent patterns.
    """
    REACT = "react"
    REFLEXION = "reflexion"
    PLAN_AND_EXECUTE = "plan_and_execute"


def create_agent(
    pattern: AgentPattern,
    model: str = "gemini-2.0-flash",
    temperature: float = 0.7
) -> Union[ReactAgent]:
    """
    Factory function to create an agent with the specified pattern.

    Args:
        pattern: The agent pattern to use
        model: Gemini model name (default: gemini-2.0-flash)
        temperature: LLM temperature (default: 0.7)

    Returns:
        An instance of the specified agent type
    """
    if pattern == AgentPattern.REACT:
        return ReactAgent(model=model, temperature=temperature)
    else:
        raise ValueError(f"Unknown agent pattern: {pattern}")


def list_available_patterns():
    """
    List all available agent patterns with descriptions.
    
    Returns:
        A dictionary mapping pattern names to their descriptions
    """
    return {
        AgentPattern.REACT: (
            "ReAct (Reasoning + Acting): The agent alternates between reasoning "
            "about what to do next and taking actions using available tools. "
            "Best for: Tasks requiring iterative tool use and dynamic decision-making."
        ),
        AgentPattern.REFLEXION: (
            "Reflexion: The agent reflects on its previous attempts, learns from "
            "mistakes, and adjusts its approach accordingly. "
            "Best for: Complex problems that may require multiple attempts to solve correctly."
        ),
        AgentPattern.PLAN_AND_EXECUTE: (
            "Plan-and-Execute: The agent first creates a comprehensive plan, "
            "then executes it step by step, adapting as needed. "
            "Best for: Multi-step tasks with clear sequential dependencies."
        )
    }


if __name__ == "__main__":
    # Example usage
    print("Available Agent Patterns:")
    print("=" * 60)
    
    patterns = list_available_patterns()
    for pattern, description in patterns.items():
        print(f"\n{pattern.value.upper()}:")
        print(f"  {description}")
    
    print("\n" + "=" * 60)
    print("\nExample: Creating a ReAct agent")
    print("  agent = create_agent(AgentPattern.REACT, model_name='gpt-4')")
    print("  result = agent.run('What is 25 * 17 + 100?')")

