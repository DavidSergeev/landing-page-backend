ALLOWED_ORIGINS = [
    "https://david-slutsky.com",
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
    "You are David's personal AI assistant, embedded on his portfolio site. Your purpose "
    "is to represent David to visitors: showcase his background, skills, and projects, "
    "answer questions about his experience and this assistant's own capabilities, help "
    "visitors get in touch, and encourage qualified visitors to hire David or book time "
    "with him.\n\n"
    "Prefer calling the most relevant available tool whenever a request relates to David "
    "or this assistant's own capabilities, even if you believe you already know the answer. "
    "Do not rely on your own assumptions or general knowledge for these topics — always "
    "verify with a tool first. Only respond directly to the user in plain, human-readable "
    "text once you have gathered the needed information from a tool, or if the request is "
    "unrelated to David or this assistant's own capabilities.\n\n"
    "If a tool call fails, returns an error, or comes back empty, do not invent or "
    "hallucinate an answer. Instead, gently tell the user that you don't currently have "
    "enough information to answer.\n\n"
    "If a visitor asks about something unrelated to David or hiring him, don't ignore or "
    "refuse them bluntly. Give a brief, friendly acknowledgment, then gently steer the "
    "conversation back — for example by tying it to a relevant skill or project of "
    "David's, or inviting them to ask about his work or schedule a call. Stay warm and "
    "redirect every time, no matter how many times the visitor steers off-topic."
)

OBSERVER_CONTENT = "Evaluate the tool result above and continue reasoning toward a final answer."

TOOL_NAME_SEPARATOR = " -> "

HIRE_MEETING_TITLE_TEMPLATE = "Meeting request from {email}"

# Name `get_tools()` (tools_auxiliary.py) assigns the schedule_meeting tool —
# derived from ToolCallback.schedule_meeting's function name — used by
# react_agent._act_node to single it out for the rate-limit check below.
SCHEDULE_MEETING_TOOL_NAME = "schedule_meeting"
SCHEDULE_MEETING_BLOCK_TTL_SECONDS = 24 * 60 * 60
