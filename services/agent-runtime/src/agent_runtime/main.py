"""Agent runtime entrypoint — starts the LangGraph agent worker loop."""
from __future__ import annotations

import asyncio
import logging
import signal
import sys

import boto3
from botocore.exceptions import ClientError

from agent_runtime.orchestrator.graph import build_itsm_resolver_graph
from agent_runtime.orchestrator.state import IncidentState
from agent_runtime.settings import Settings

logger = logging.getLogger(__name__)

settings = Settings()


def _configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )


async def _process_incident_message(message: dict, graph: object) -> None:
    """Process a single incident message from SQS."""
    body = message.get("Body", "{}")
    import json

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in SQS message: %s", body[:200])
        return

    incident_id = event.get("incident_id", "unknown")
    logger.info("Processing incident %s", incident_id)

    initial_state = IncidentState(
        incident_id=incident_id,
        title=event.get("title", ""),
        description=event.get("description", ""),
        priority=event.get("priority", "P3"),
    )

    try:
        final_state = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: graph.invoke(initial_state),
        )
        logger.info(
            "Incident %s resolved: status=%s ticket=%s",
            incident_id,
            final_state.get("status"),
            final_state.get("ticket_id"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error processing incident %s: %s", incident_id, exc)


async def _poll_sqs(queue_url: str, graph: object) -> None:
    """Poll SQS queue for incident messages and dispatch to graph."""
    sqs = boto3.client("sqs", region_name=settings.aws_region)
    logger.info("Polling SQS queue: %s", queue_url)

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=20,
                AttributeNames=["All"],
            )
            messages = response.get("Messages", [])

            for message in messages:
                await _process_incident_message(message, graph)
                # Delete after processing
                try:
                    sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message["ReceiptHandle"],
                    )
                except ClientError as exc:
                    logger.warning("Failed to delete SQS message: %s", exc)

        except ClientError as exc:
            logger.error("SQS poll error: %s", exc)
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("SQS polling cancelled — shutting down")
            break


def main() -> None:
    """Start the agent runtime worker."""
    _configure_logging()

    logger.info("Agent runtime starting — model=%s", settings.model_id)

    graph = build_itsm_resolver_graph()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    task = loop.create_task(
        _poll_sqs(settings.incident_queue_url, graph)
    )

    def _shutdown(sig: int, _: object) -> None:
        logger.info("Signal %s received — cancelling worker", sig)
        task.cancel()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        loop.run_until_complete(task)
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()
        logger.info("Agent runtime stopped")


if __name__ == "__main__":
    main()
