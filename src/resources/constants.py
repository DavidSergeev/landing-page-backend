DEFAULT_MODEL = "gemini-2.0-flash"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

REASON = "reason"
ACT = "act"
FINALIZE = "finalize"
CONTINUE = "continue"
END = "end"
FINAL_ANSWER = "Final Answer"

SYSTEM_PROMPT = (
    "You are David's personal AI assistant on his portfolio landing page. "
    "You are helpful, concise, and professional. "
    "Answer questions about David, his work, and general topics. "
    "Keep responses clear and well-structured. "
    "If asked about David's background, skills, or projects, be positive and informative."
)

OBSERVER_CONTENT = "Evaluate the tool result above and continue reasoning toward a final answer."
