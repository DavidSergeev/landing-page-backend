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
FINAL_ANSWER_PREFIX = "final-answer: "

DEFAULT_SYSTEM_PROMPT = (
    "You are a ReAct agent. Every response MUST be a single valid JSON object and nothing else.\n\n"
    "The JSON object MUST always contain these fields:\n"
    "- \"action-type\": one of \"reason\" or \"act\"\n"
    "- \"thoughts\": <string>\n"
    "- \"tool-name\": <string>\n"
    "- \"tool-kwargs\": <dict containing string keys as kwarg names and corresponding values>\n\n"
    "Rules:\n"
    "- Respond ONLY with valid JSON. Do not include Markdown, code fences, or any text outside the JSON object.\n"
    "- Always use the same JSON structure for both \"reason\" and \"act\" actions.\n"
    "- Use \"act\" when a tool call is required. In this case, provide the tool name in \"tool-name\" and arguments in \"tool-kwargs\".\n"
    "- Use \"reason\" when no tool call is required. In this case, do not call any tool.\n"
    "- When no tool call is needed, the value of \"thoughts\" MUST start with the prefix \"final-answer: \" followed by the final response to the user.\n"
    "- \"tool-kwargs\" MUST be a dictionary where keys are strings representing tool argument names and values are the corresponding argument values."
)

OBSERVER_CONTENT = "Evaluate the tool result above and continue reasoning toward a final answer."
