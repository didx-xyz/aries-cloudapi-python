from typing import List
from fastapi import FastAPI, Request, Depends, APIRouter
from dependency_injector.wiring import inject, Provide
from containers import Container
from fastapi_websocket_pubsub import PubSubEndpoint
from starlette.websockets import WebSocket

from containers import Container as RedisContainer
from services import Service, TopicItem

import logging
from pprint import pformat
import os
import sys

LOG_LEVEL = os.getenv("LOG_LEVEL", "error")
log = logging.getLogger(__name__)


app = FastAPI()
router = APIRouter()
endpoint = PubSubEndpoint()
endpoint.register_route(router, "/pubsub")
app.include_router(router)


@app.api_route("/{topic}")
@inject
async def index(
    topic: str, service: Service = Depends(Provide[Container.service])
) -> List[TopicItem]:
    return await service.get_all_by_topic(topic)


@app.api_route("/{topic}/{wallet_id}")
@inject
async def wallet_hooks(
    topic: str, wallet_id: str, service=Depends(Provide[Container.service])
) -> List[TopicItem]:
    data = await service.get_all_for_topic_by_wallet_id(
        topic=topic, wallet_id=wallet_id
    )
    await endpoint.publish(topics=[topic, wallet_id], data=data)
    return data


@app.api_route("/{wallet_id}}")
@inject
async def wallet_root(
    wallet_id: str, service: Service = Depends(Provide[Container.service])
) -> dict:
    value = await service.get_all_by_topic(f"{wallet_id}")
    return {f"{wallet_id}": value}


@app.post("/topic/{topic}")
@inject
async def topic_root(
    topic, request: Request, service: Service = Depends(Provide[Container.service])
):
    payload = await request.json()
    wallet_id = {"wallet_id": (request.headers)["x-wallet-id"]}
    payload.update(wallet_id)
    payload = pformat(payload)
    await service.add_topic_entry(str(topic), str(payload))
    await endpoint.publish(topics=[topic, wallet_id["wallet_id"]], data=payload)
    getattr(log, LOG_LEVEL)(f"{topic}:\n{payload}")


@app.post("/{wallet_id}/topic/{topic}")
async def topic_wallet(
    wallet_id,
    topic,
    request: Request,
    service: Service = Depends(Provide[Container.service]),
):
    payload = pformat(await request.json())
    await service.add_topic_entry(wallet_id, str(payload))
    await endpoint.publish(topics=[topic, wallet_id], data=payload)
    getattr(log, LOG_LEVEL)(f"Wallet {wallet_id}\n{topic}:\n{payload}")


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
