"""
Shared "one meeting per user" cooldown, enforced identically wherever
`ToolCallback.schedule_meeting` can be reached: the direct /schedule-meeting
endpoint and the agent's schedule_meeting tool call (see main.py and
react_agent.py's _act_node, respectively).

Identity is the caller's attendee_email when given — it identifies the
person, not just their network/device — falling back to their IP (forwarded
by landing-api-worker as the signed `x-real-ip` header) when no email was
supplied, e.g. an anonymous chat visitor who never gave one.
"""
from typing import Optional
from src.db import rate_limit_repository
import src.resources.constants as constant


def resolve_identity(email: Optional[str], ip: Optional[str]) -> Optional[str]:
    """None only when neither signal is available — callers are never blocked in that case."""
    return email or ip or None


def is_blocked(identity: Optional[str]) -> bool:
    if not identity:
        return False
    return rate_limit_repository.is_blocked(identity)


def mark_blocked(identity: Optional[str]) -> None:
    if identity:
        rate_limit_repository.mark_blocked(identity, constant.SCHEDULE_MEETING_BLOCK_TTL_SECONDS)
