ALLOWED_ORIGINS = [
    "https://davidsergeev.github.io",
    "http://localhost:5173",
]

DEFAULT_MODEL = "gemini-3.1-flash-lite"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

REASON = "reason"
ACT = "act"
FINALIZE = "finalize"
CONTINUE = "continue"
END = "end"

DEFAULT_SYSTEM_PROMPT = (
    "You are a ReAct agent that can call tools to help answer questions.\n\n"
    "When you need information you don't have, call the most relevant available tool. "
    "When you have enough information to answer, respond directly to the user in plain, "
    "human-readable text instead of calling a tool."
)

OBSERVER_CONTENT = "Evaluate the tool result above and continue reasoning toward a final answer."

TOOL_NAME_SEPARATOR = " -> "
