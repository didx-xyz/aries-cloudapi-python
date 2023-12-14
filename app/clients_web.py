import asyncio
import os
import sys
import json
import aioredis
from aioredis import Redis
from httpx import AsyncClient, HTTPStatusError

from typing import Any, Dict
from pydantic import BaseModel
from aries_cloudcontroller import AcaPyClient, TransactionRecord
from shared.util.rich_parsing import parse_with_error_handling

from shared.constants import GOVERNANCE_AGENT_API_KEY, GOVERNANCE_AGENT_URL

from fastapi_websocket_pubsub import PubSubClient

LAGO_URL = "http://localhost:3000/api/v1/events"
LAGO_API_KEY = "cb131628-c605-49bd-8aa3-93fe0289e1a3"
PORT = os.getenv("PORT", "3010")
URL = os.getenv("WEBHOOKS_URL", "localhost")
