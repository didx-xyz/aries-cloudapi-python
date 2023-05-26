import json
from typing import Any, Dict, List
from pprint import pformat

from fastapi import FastAPI, Request, Depends, APIRouter
from dependency_injector.wiring import inject, Provide
from containers import Container
from fastapi_websocket_pubsub import PubSubEndpoint

from containers import Container as RedisContainer
from services import Service
from shared_models import TopicItem, topic_mapping, RedisItem, WEBHOOK_TOPIC_ALL

import logging
import os
import sys

OPENAPI_NAME = os.getenv("OPENAPI_NAME", "Webhooks")
PROJECT_VERSION = os.getenv("PROJECT_VERSION", "0.0.1BETA")
LOG_LEVEL = os.getenv("LOG_LEVEL", "error")
log = logging.getLogger(__name__)


app = FastAPI(
    title=OPENAPI_NAME,
    description="Welcome to the OpenAPI interface for the AriesCloudAPI webhooks handler",
    version=PROJECT_VERSION,
)
router = APIRouter()
endpoint = PubSubEndpoint()
endpoint.register_route(router, "/pubsub")
app.include_router(router)


@app.api_route("/{topic}/{wallet_id}")
@inject
async def wallet_hooks(
    topic: str, wallet_id: str, service: Service = Depends(Provide[Container.service])
) -> List[TopicItem[Any]]:
    data = await service.get_all_for_topic_by_wallet_id(
        topic=topic, wallet_id=wallet_id
    )
    return data


@app.api_route("/{wallet_id}")
@inject
async def wallet_root(
    wallet_id: str, service: Service = Depends(Provide[Container.service])
):
    data = await service.get_all_by_wallet(wallet_id)
    return data


# 'origin' helps to distinguish where a hook is from
# eg the admin, tenant or OP agent respectively
@app.post("/{origin}/topic/{acapy_topic}", status_code=204)
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
        log.debug(
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
        log.debug(
            "Not publishing webhook event for topic %s as no transformer exists for the topic",
            topic,
        )
        return

    # publish the webhook to subscribers for the following topics
    #  - current wallet id
    #  - topic of the event
    #  - topic and wallet id combined as topic-wallet_id (this allows for fine grained subscriptions (i.e. the endorser service))
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

    log.debug("%s:\n%s", topic, pformat(webhook_event))


# Example for broadcasting from eg Redis
# @router.websocket("/pubsub")
# async def websocket_rpc_endpoint(websocket: WebSocket):
#     async with endpoint.broadcaster:
#         await endpoint.main_loop(websocket)

app.include_router(router)

container = RedisContainer()
container.config.redis_host.from_env("REDIS_HOST", "wh-redis")
container.config.redis_password.from_env("REDIS_PASSWORD", "")
container.wire(modules=[sys.modules[__name__]])
