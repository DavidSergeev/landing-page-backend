"""
Shared boto3 DynamoDB resource — one instance per Lambda container.
Reused across warm invocations to avoid repeated connection overhead.
"""
import os
import boto3
from boto3.resources.base import ServiceResource

_resource: ServiceResource = boto3.resource("dynamodb")


def get_table(env_var: str):
    """Return a DynamoDB Table object using the table name from env_var."""
    table_name = os.environ[env_var]
    return _resource.Table(table_name)
