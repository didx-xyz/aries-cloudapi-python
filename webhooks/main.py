from fastapi import FastAPI, Request
import logging
from pprint import pformat
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

app = FastAPI()

log = logging.getLogger(__name__)


@app.post("/topic/{topic}")
async def topic_root(topic, request: Request):
    payload = pformat(await request.json())
    getattr(log, LOG_LEVEL)(f"{topic}:\n{payload}")
