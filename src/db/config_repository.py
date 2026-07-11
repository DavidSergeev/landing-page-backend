"""
CRUD operations for the landing-config DynamoDB table.
Items are keyed by config_key (e.g. "system_info", "user_info").
"""
from typing import Optional
from boto3.dynamodb.conditions import Key
from src.db.dynamo_client import get_table
from src.service_utils.logger import get_logger

logger = get_logger()

_TABLE_ENV_VAR = "CONFIG_TABLE_NAME"


def get_config(config_key: str) -> Optional[str]:
    """Fetch a config value by key. Returns None if not found."""
    table = get_table(_TABLE_ENV_VAR)
    response = table.get_item(Key={"config_key": config_key})
    item = response.get("Item")
    if item is None:
        logger.warning("Config key not found: %s", config_key)
        return None
    return item.get("value")


def set_config(config_key: str, value: str) -> None:
    """Insert or overwrite a config item."""
    table = get_table(_TABLE_ENV_VAR)
    table.put_item(Item={"config_key": config_key, "value": value})
    logger.info("Config key set: %s", config_key)
