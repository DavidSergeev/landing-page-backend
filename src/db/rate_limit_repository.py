"""
CRUD operations for the landing-rate-limits DynamoDB table.
Items are keyed by a SHA-256 hash of the caller's identity (email or IP) —
the raw value is never stored — and self-expire via the table's native TTL
attribute. `blocked_until`, not item existence, is the actual gate: DynamoDB's
TTL sweep can lag up to ~48h past expiry, so a lingering item must not still
count as blocked.
"""
import hashlib
import time
from src.db.dynamo_client import get_table
from src.service_utils.logger import get_logger

logger = get_logger()

_TABLE_ENV_VAR = "RATE_LIMITS_TABLE_NAME"
_TTL_CLEANUP_BUFFER_SECONDS = 172800


def _hash_identity(identity: str) -> str:
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def is_blocked(identity: str) -> bool:
    """True if `identity` is still within an active cooldown window."""
    table = get_table(_TABLE_ENV_VAR)
    item = table.get_item(Key={"identity_hash": _hash_identity(identity)}).get("Item")
    return bool(item) and item["blocked_until"] > int(time.time())


def mark_blocked(identity: str, ttl_seconds: int) -> None:
    """Start a `ttl_seconds`-long cooldown for `identity`."""
    table = get_table(_TABLE_ENV_VAR)
    now = int(time.time())
    table.put_item(Item={
        "identity_hash": _hash_identity(identity),
        "blocked_until": now + ttl_seconds,
        "ttl": now + ttl_seconds + _TTL_CLEANUP_BUFFER_SECONDS,
    })
    logger.info("Rate-limit cooldown started for %ds", ttl_seconds)
