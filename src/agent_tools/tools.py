"""
Tool callbacks invoked by the LangGraph agent.

get_relevant_info's USER/SYSTEM branches are cached at module load (Lambda cold
start) so subsequent warm invocations skip DynamoDB entirely. Its CHOSEN_COMPANY
branch is looked up directly on every call instead — no cache needed since it's
a DynamoDB GetItem on a hash key, already O(1) regardless of how many companies
are stored.
schedule_meeting writes a new record on every call and sends a notification
email (Gmail credentials are fetched from SSM once and cached — see email_client).
"""
from datetime import datetime
from typing import Optional
from src.db import config_repository, meetings_repository
from src.service_utils import email_client
from src.service_utils.logger import get_logger
from enum import Enum


logger = get_logger()

# Populated on first call, reused for the lifetime of the Lambda container.
_CONFIG_CACHE: dict[str, Optional[str]] = {}


class MeetingScheduledStatus:
    """Short, agent-readable outcomes for `ToolCallback.schedule_meeting`."""
    NOT_SCHEDULED: str = "the meeting is not scheduled"
    MEETING_SAVED: str = "the meeting is saved in db but email not sent"
    SCHEDULED: str = "the meeting is scheduled"


class RelevantInfoType(str, Enum):
    """String-valued so Pydantic emits a string `enum` in the tool's JSON schema —
    Gemini's function-calling `Schema.enum` only accepts strings, not ints."""
    USER = "user"
    SYSTEM = "system"
    CHOSEN_COMPANY = "chosen_company"

class ToolCallback:

    @staticmethod
    def get_relevant_info(info_type: RelevantInfoType, company_name: Optional[str] = None) -> Optional[str]:
        """
        Retrieve contextual information for the assistant. Args: info_type (required, a
        RelevantInfoType — USER for David's profile: background, skills, projects, contact
        details; SYSTEM for this assistant's runtime/environment info; CHOSEN_COMPANY for
        why David chose to send his CV to a specific company), company_name (required only
        when info_type is CHOSEN_COMPANY — the company's name; ignored otherwise). Returns
        a JSON string with the requested info, or None if not configured. Raises an
        exception if company_name is missing while info_type is CHOSEN_COMPANY, or if
        info_type is not a recognized RelevantInfoType.
        Use this when answering questions about David's experience/work/contact info
        (USER), about the current environment or assistant capabilities (SYSTEM), or about
        why David applied to a specific company (CHOSEN_COMPANY).
        """
        info: Optional[str] = None
        if info_type == RelevantInfoType.USER:
            if "user_info" not in _CONFIG_CACHE:
                _CONFIG_CACHE["user_info"] = config_repository.get_config("user_info")
                logger.info("user_info loaded from DynamoDB")
            info = _CONFIG_CACHE["user_info"]
        elif info_type == RelevantInfoType.SYSTEM:
            if "system_info" not in _CONFIG_CACHE:
                _CONFIG_CACHE["system_info"] = config_repository.get_config("system_info")
                logger.info("system_info loaded from DynamoDB")
            info = _CONFIG_CACHE["system_info"]
        elif info_type == RelevantInfoType.CHOSEN_COMPANY:
            if not company_name:
                raise ValueError("company_name is required when info_type is CHOSEN_COMPANY")
            # No cache: a DynamoDB GetItem on a hash key is already O(1), so caching
            # per-company lookups would only add staleness risk with no speed benefit.
            config_key = f"company_info:{company_name.strip().lower()}"
            info = config_repository.get_config(config_key)
            logger.info("company_info loaded from DynamoDB for %s", company_name)
        else:
            raise ValueError(f"Unknown RelevantInfoType: {info_type}")

        return info

    @staticmethod
    def schedule_meeting(
        title: str,
        scheduled_at: datetime,
        description: Optional[str] = None,
        attendee_email: Optional[str] = None,
    ) -> str:
        """
        Schedule a meeting, persist it, and email a notification. Args: title (required, str),
        scheduled_at (required, ISO-8601 datetime), description (optional, str — agenda or notes),
        attendee_email (optional, str — visitor's email address).
        Returns a short status string describing the outcome — see `MeetingScheduledStatus`
        (not scheduled, saved but email failed, or fully scheduled). Use this when the user
        asks to book, schedule, or set up a meeting with David.
        """
        try:
            meeting_id = meetings_repository.save_meeting(
                title=title,
                scheduled_at=scheduled_at,
                description=description,
                attendee_email=attendee_email,
            )
            logger.info("Meeting scheduled: %s", meeting_id)
        except Exception as e:
            logger.error("Failed to schedule meeting: %s", e)
            return MeetingScheduledStatus.NOT_SCHEDULED

        try:
            email_client.send_meeting_notification(title, scheduled_at, description, attendee_email)
        except Exception as e:
            logger.error("Failed to send meeting notification email: %s", e)
            return MeetingScheduledStatus.MEETING_SAVED

        return MeetingScheduledStatus.SCHEDULED
