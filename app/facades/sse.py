import asyncio
from typing import AsyncGenerator

from fastapi import Request
from httpx import AsyncClient, HTTPError, Response, Timeout

from shared import WEBHOOKS_URL

SSE_PING_PERIOD = 15
# SSE sends a ping every 15 seconds, so user will get at least one message within this timeout
default_timeout = Timeout(SSE_PING_PERIOD, read=3600.0)  # 1 hour read timeout


async def sse_subscribe_wallet(wallet_id: str) -> AsyncGenerator[str, None]:
    """
    Subscribe to server-side events for a specific wallet ID.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
    """
    try:
        async with AsyncClient(timeout=default_timeout) as client:
            async with client.stream(
                "GET", f"{WEBHOOKS_URL}/sse/{wallet_id}"
            ) as response:
                async for line in response.aiter_lines():
                    yield line + "/n"
    except HTTPError as e:
        raise e from e


async def sse_subscribe_wallet_topic(
    wallet_id: str, topic: str
) -> AsyncGenerator[str, None]:
    """
    Subscribe to server-side events for a specific wallet ID and topic.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
        topic: The topic to which the wallet is subscribing.
    """
    try:
        async with AsyncClient(timeout=default_timeout) as client:
            async with client.stream(
                "GET", f"{WEBHOOKS_URL}/sse/{wallet_id}/{topic}"
            ) as response:
                async for line in response.aiter_lines():
                    yield line
    except HTTPError as e:
        raise e from e


async def sse_subscribe_event_with_state(
    wallet_id: str,
    topic: str,
    desired_state: str,
) -> AsyncGenerator[str, None]:
    """
    Subscribe to server-side events for a specific wallet ID and topic.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
        topic: The topic to which the wallet is subscribing.
    """
    try:
        async with AsyncClient(timeout=default_timeout) as client:
            async with client.stream(
                "GET", f"{WEBHOOKS_URL}/sse/{wallet_id}/{topic}/{desired_state}"
            ) as response:
                async for line in response.aiter_lines():
                    yield line
    except HTTPError as e:
        raise e from e


async def sse_subscribe_stream_with_fields(
    wallet_id: str,
    topic: str,
    field: str,
    field_id: str,
) -> AsyncGenerator[str, None]:
    """
    Subscribe to server-side events for a specific wallet ID and topic.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
        topic: The topic to which the wallet is subscribing.
    """
    try:
        async with AsyncClient(timeout=default_timeout) as client:
            async with client.stream(
                "GET", f"{WEBHOOKS_URL}/sse/{wallet_id}/{topic}/{field}/{field_id}"
            ) as response:
                async for line in response.aiter_lines():
                    yield line
    except HTTPError as e:
        raise e from e


async def sse_subscribe_event_with_field_and_state(
    wallet_id: str,
    topic: str,
    field: str,
    field_id: str,
    desired_state: str,
) -> AsyncGenerator[str, None]:
    """
    Subscribe to server-side events for a specific wallet ID and topic.

    Args:
        wallet_id: The ID of the wallet subscribing to the events.
        topic: The topic to which the wallet is subscribing.
    """
    try:
        async with AsyncClient(timeout=default_timeout) as client:
            async with client.stream(
                "GET",
                f"{WEBHOOKS_URL}/sse/{wallet_id}/{topic}/{field}/{field_id}/{desired_state}",
            ) as response:
                async for line in response.aiter_lines():
                    yield line
    except HTTPError as e:
        raise e from e
