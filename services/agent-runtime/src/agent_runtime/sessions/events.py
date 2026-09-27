"""Session event emission — CloudEvents formatted audit trail."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

from agent_runtime.settings import Settings

logger = logging.getLogger(__name__)

_settings = Settings()


def emit_session_event(
    event_type: str,
    subject: str,
    data: dict[str, Any],
) -> bool:
    """Emit a CloudEvent to the change events SQS queue.

    Args:
        event_type: CloudEvent type (e.g., incident.resolved)
        subject: Event subject (e.g., incident_id)
        data: Event payload

    Returns:
        True if emitted successfully, False otherwise.
    """
    event = {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "type": event_type,
        "source": "urn:it-control-plane:agent-runtime",
        "subject": subject,
        "time": datetime.now(tz=timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "data": data,
    }

    if not _settings.change_events_queue_url:
        logger.debug("No change events queue configured — skipping event emission")
        return False

    try:
        sqs = boto3.client("sqs", region_name=_settings.aws_region)
        sqs.send_message(
            QueueUrl=_settings.change_events_queue_url,
            MessageBody=json.dumps(event),
            MessageGroupId=subject,
            MessageDeduplicationId=event["id"],
        )
        logger.info("Emitted event %s for subject %s", event_type, subject)
        return True
    except ClientError as exc:
        logger.warning("Failed to emit session event: %s", exc)
        return False
