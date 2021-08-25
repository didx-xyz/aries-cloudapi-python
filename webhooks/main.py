from fastapi import FastAPI, Request, Depends, APIRouter
from dependency_injector.wiring import inject, Provide
from fastapi_websocket_pubsub import PubSubEndpoint
from starlette.websockets import WebSocket

from .containers import Container
from .services import Service

import logging
from pprint import pformat
import os
import sys

LOG_LEVEL = os.getenv("LOG_LEVEL", "error")
log = logging.getLogger(__name__)


app = FastAPI()
router = APIRouter()
endpoint = PubSubEndpoint(broadcaster="redis://wh-redis:6379")


@app.api_route("/{topic}")
@inject
async def index(
    topic: str, service: Service = Depends(Provide[Container.service])
) -> dict:
    value = await service.get_all_by_topic(f"{topic}")
    return {f"{topic}": value}


@app.api_route("/{wallet_id}}")
@inject
async def index(
    wallet_id: str, service: Service = Depends(Provide[Container.service])
) -> dict:
    value = await service.get_all_by_topic(f"{wallet_id}")
    return {f"{wallet_id}": value}


@app.post("/topic/{topic}")
@inject
async def topic_root(
    topic, request: Request, service: Service = Depends(Provide[Container.service])
):
    payload = pformat(await request.json())
    await service.add_topic_entry(str(topic), str(payload))
    await endpoint.publish(topics=[topic], data=payload)
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


@router.websocket("/pubsub")
async def websocket_rpc_endpoint(websocket: WebSocket):
    async with endpoint.broadcaster:
        await endpoint.main_loop(websocket)


# TODO: Figure out how this can possibly work using webhooks
# According to the docs this is supported
# @app.websocket("/")
# async def websocket_topics(websocket: WebSocket):
#     await websocket.accept()
#     while True:
#         log.error("Websocket root: \n")
#         data = websocket.receive_text()
#         getattr(log, LOG_LEVEL)(f"\n{data}")

app.include_router(router)

container = Container()
container.config.redis_host.from_env("REDIS_HOST", "wh-redis")
container.config.redis_password.from_env("REDIS_PASSWORD", "")
container.wire(modules=[sys.modules[__name__]])
