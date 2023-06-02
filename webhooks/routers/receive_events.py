import json
import logging
from pprint import pformat
from typing import Any, Dict

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request, status
from fastapi_websocket_pubsub import PubSubEndpoint

from webhooks.dependencies.container import Container
from webhooks.dependencies.service import Service

LOGGER = logging.getLogger(__name__)


endpoint = PubSubEndpoint()
endpoint.register_route(router, "/pubsub")


# 'origin' helps to distinguish where a hook is from
# eg the admin, tenant or OP agent respectively
@router.post(
    "/{origin}/topic/{acapy_topic}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Receive webhook events from ACA-Py",
)
@router.post(
    "/{origin}/topic/{acapy_topic}/",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
@inject
async def topic_root(
    acapy_topic: str,
    origin: str,
    body: Dict[str, Any],
    request: Request,
    service: Service = Depends(Provide[Container.service]),
):
    try:
        wallet_id = request.headers["x-wallet-id"]
    except KeyError:
        wallet_id = "admin"

    # We need to map from the acapy webhook topic to a unified cloud api topic. If the topic doesn't exist in the topic
    # mapping it means we don't support the webhook event yet and we will ignore it for now. This allows us to add more
    # webhook events as needed, without needing to break any models
    topic = topic_mapping.get(acapy_topic)
    if not topic:
        LOGGER.warning(
            "Not publishing webhook event for acapy_topic %s as it doesn't exist in the topic_mapping",
            acapy_topic,
        )
        return

    redis_item: RedisItem = RedisItem(
        payload=body,
        origin=origin,
        topic=topic,
        acapy_topic=acapy_topic,
        wallet_id=wallet_id,
    )

    webhook_event = await service.transform_topic_entry(redis_item)
    if not webhook_event:
        LOGGER.warning(
            "Not publishing webhook event for topic %s as no transformer exists for the topic",
            topic,
        )
        return

    # publish the webhook to subscribers for the following topics
    #  - current wallet id
    #  - topic of the event
    #  - topic and wallet id combined as topic-wallet_id
    #    - this allows for fine grained subscriptions (i.e. the endorser service)
    #  - 'all' topic, which allows to subscribe to all published events
    # FIXME: wallet_id is admin for all admin wallets from different origins. We should make a difference on this
    # Maybe the wallet id should be the role (governance, tenant-admin)?
    await endpoint.publish(
        topics=[
            topic,
            redis_item["wallet_id"],
            f"{topic}-{redis_item['wallet_id']}",
            WEBHOOK_TOPIC_ALL,
        ],
        data=webhook_event.json(),
    )
    # Add data to redis
    await service.add_topic_entry(redis_item["wallet_id"], json.dumps(redis_item))

    LOGGER.debug("%s:\n%s", topic, pformat(webhook_event))
