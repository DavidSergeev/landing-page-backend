"""
Tool callbacks invoked by the LangGraph agent.

get_sys_info and get_user_info are cached at module load (Lambda cold start)
so subsequent warm invocations skip DynamoDB entirely.
schedule_meeting writes a new record on every call and sends a notification
email (Gmail credentials are fetched from SSM once and cached — see email_client).
"""
from datetime import datetime
from typing import Optional
from src.db import config_repository, meetings_repository
from src.service_utils import email_client
from src.service_utils.logger import get_logger

logger = get_logger()

# Populated on first call, reused for the lifetime of the Lambda container.
_CONFIG_CACHE: dict[str, Optional[str]] = {}


class MeetingScheduledStatus:
    """Short, agent-readable outcomes for `ToolCallback.schedule_meeting`."""
    NOT_SCHEDULED: str = "the meeting is not scheduled"
    MEETING_SAVED: str = "the meeting is saved in db but email not sent"
    SCHEDULED: str = "the meeting is scheduled"


class ToolCallback:

    @staticmethod
    def get_sys_info() -> Optional[str]:
        """
        Retrieve system-level context about the assistant's environment (e.g. runtime info, deployment stage).
        No args required. Returns a JSON string with system metadata, or None if not configured.
        Use this before answering questions that depend on the current environment or assistant capabilities.
        """
        if "system_info" not in _CONFIG_CACHE:
            _CONFIG_CACHE["system_info"] = config_repository.get_config("system_info")
            logger.info("system_info loaded from DynamoDB")
        return _CONFIG_CACHE["system_info"]

    @staticmethod
    def get_user_info() -> Optional[str]:
        """
        Retrieve profile information about David (owner of this assistant): background, skills, projects, contact details.
        No args required. Returns a JSON string with profile data, or None if not configured.
        Use this when answering questions about David's experience, work, or how to get in touch.
        """
        if "user_info" not in _CONFIG_CACHE:
            _CONFIG_CACHE["user_info"] = config_repository.get_config("user_info")
            logger.info("user_info loaded from DynamoDB")
        return _CONFIG_CACHE["user_info"]

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
