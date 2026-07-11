"""
Write and query operations for the landing-meetings DynamoDB table.
PK: meeting_id (UUID), SK: scheduled_at (ISO-8601 string).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from src.db.dynamo_client import get_table
from src.service_utils.logger import get_logger

logger = get_logger()

_TABLE_ENV_VAR = "MEETINGS_TABLE_NAME"


def save_meeting(
    title: str,
    scheduled_at: datetime,
    description: Optional[str] = None,
    attendee_email: Optional[str] = None,
) -> str:
    """
    Persist a new meeting. Returns the generated meeting_id.
    scheduled_at is stored as an ISO-8601 UTC string.
    """
    meeting_id = str(uuid.uuid4())
    scheduled_at_str = scheduled_at.astimezone(timezone.utc).isoformat()

    item: dict = {
        "meeting_id": meeting_id,
        "scheduled_at": scheduled_at_str,
        "title": title,
    }
    if description:
        item["description"] = description
    if attendee_email:
        item["attendee_email"] = attendee_email

    table = get_table(_TABLE_ENV_VAR)
    table.put_item(Item=item)
    logger.info("Meeting saved: %s at %s", meeting_id, scheduled_at_str)
    return meeting_id


def list_meetings() -> list[dict]:
    """Return all meetings ordered by scheduled_at ascending."""
    table = get_table(_TABLE_ENV_VAR)
    response = table.scan()
    items = response.get("Items", [])
    return sorted(items, key=lambda m: m["scheduled_at"])
