import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrNoServers, ErrTimeout
from nats.errors import BadSubscriptionError, Error, TimeoutError
from nats.js.client import JetStreamContext

from shared.constants import NATS_STREAM, NATS_SUBJECT
from shared.models.webhook_events import CloudApiWebhookEventGeneric
from waypoint.services.nats_service import NatsEventsProcessor, init_nats_client


@pytest.fixture
async def mock_nats_client():
    with patch("nats.connect") as mock_connect:
        mock_nats = AsyncMock(spec=NATS)
        mock_jetstream = AsyncMock(spec=JetStreamContext)
        mock_nats.jetstream.return_value = mock_jetstream
        mock_connect.return_value = mock_nats
        yield mock_jetstream


@pytest.mark.anyio
@pytest.mark.parametrize("nats_creds_file", [None, "some_file"])
async def test_init_nats_client(nats_creds_file):
    mock_nats_client = AsyncMock(spec=NATS)  # pylint: disable=redefined-outer-name

    with patch("nats.connect", return_value=mock_nats_client), patch(
        "waypoint.services.nats_service.NATS_CREDS_FILE", new=nats_creds_file
    ):
        async for jetstream in init_nats_client():
            assert jetstream == mock_nats_client.jetstream.return_value


@pytest.mark.anyio
@pytest.mark.parametrize("exception", [ErrConnectionClosed, ErrTimeout, ErrNoServers])
async def test_init_nats_client_error(exception):
    with patch("nats.connect", side_effect=exception):
        with pytest.raises(exception):
            async for jetstream in init_nats_client():
                pass


@pytest.mark.anyio
async def test_nats_events_processor_subscribe(
    mock_nats_client,  # pylint: disable=redefined-outer-name
):
    processor = NatsEventsProcessor(mock_nats_client)
    mock_nats_client.pull_subscribe.return_value = AsyncMock(
        spec=JetStreamContext.PullSubscription
    )

    subscription = await processor._subscribe(  # pylint: disable=protected-access
        "group_id", "wallet_id"
    )
    mock_nats_client.pull_subscribe.assert_called_once_with(
        subject=f"{NATS_SUBJECT}.group_id.wallet_id", stream=NATS_STREAM
    )
    assert isinstance(subscription, JetStreamContext.PullSubscription)


@pytest.mark.anyio
@pytest.mark.parametrize("exception", [BadSubscriptionError, Error, Exception])
async def test_nats_events_processor_subscribe_error(
    mock_nats_client, exception  # pylint: disable=redefined-outer-name
):
    processor = NatsEventsProcessor(mock_nats_client)
    mock_nats_client.pull_subscribe.side_effect = exception

    with pytest.raises(exception):
        await processor._subscribe("group_id", "wallet_id")


@pytest.mark.anyio
@pytest.mark.parametrize("group_id", [None, "group_id"])
async def test_process_events(
    mock_nats_client, group_id  # pylint: disable=redefined-outer-name
):
    processor = NatsEventsProcessor(mock_nats_client)
    mock_subscription = AsyncMock()
    mock_nats_client.pull_subscribe.return_value = mock_subscription

    mock_message = AsyncMock()
    mock_message.headers = {"event_topic": "test_topic"}
    mock_message.data = json.dumps(
        {
            "wallet_id": "some_wallet_id",
            "group_id": "group_id",
            "origin": "multitenant",
            "topic": "some_topic",
            "payload": {"field": "value", "state": "state"},
        }
    )
    mock_subscription.fetch.return_value = [mock_message]

    stop_event = asyncio.Event()
    async with processor.process_events(
        group_id, "wallet_id", "test_topic", stop_event, duration=1
    ) as event_generator:
        events = []
        async for event in event_generator:
            events.append(event)
            stop_event.set()

    assert len(events) == 1
    assert isinstance(events[0], CloudApiWebhookEventGeneric)
    assert events[0].payload["field"] == "value"

    mock_subscription.fetch.assert_called()
    mock_message.ack.assert_called_once()


@pytest.mark.anyio
async def test_process_events_cancelled_error(
    mock_nats_client,  # pylint: disable=redefined-outer-name
):
    processor = NatsEventsProcessor(mock_nats_client)
    mock_subscription = AsyncMock()
    mock_nats_client.pull_subscribe.return_value = mock_subscription

    stop_event = asyncio.Event()

    with patch.object(mock_subscription, "fetch", side_effect=asyncio.CancelledError):
        async with processor.process_events(
            "group_id", "wallet_id", "test_topic", stop_event, duration=1
        ) as event_generator:
            events = []
            async for event in event_generator:
                events.append(event)

    assert len(events) == 0
    assert stop_event.is_set()


@pytest.mark.anyio
async def test_process_events_timeout_error(
    mock_nats_client,  # pylint: disable=redefined-outer-name
):
    processor = NatsEventsProcessor(mock_nats_client)
    mock_subscription = AsyncMock()
    mock_nats_client.pull_subscribe.return_value = mock_subscription

    mock_subscription.fetch.side_effect = TimeoutError

    stop_event = asyncio.Event()
    async with processor.process_events(
        "group_id", "wallet_id", "test_topic", stop_event, duration=1
    ) as event_generator:
        events = []
        async for event in event_generator:
            events.append(event)

    assert len(events) == 0
    assert stop_event.is_set()


@pytest.mark.anyio
async def test_check_jetstream_working(
    mock_nats_client,  # pylint: disable=redefined-outer-name
):
    processor = NatsEventsProcessor(mock_nats_client)
    mock_nats_client.account_info.return_value = AsyncMock(streams=2, consumers=5)

    result = await processor.check_jetstream()

    assert result == {
        "is_working": True,
        "streams_count": 2,
        "consumers_count": 5,
    }
    mock_nats_client.account_info.assert_called_once()


@pytest.mark.anyio
async def test_check_jetstream_no_streams(
    mock_nats_client,  # pylint: disable=redefined-outer-name
):
    processor = NatsEventsProcessor(mock_nats_client)
    mock_nats_client.account_info.return_value = AsyncMock(streams=0, consumers=0)

    result = await processor.check_jetstream()

    assert result == {
        "is_working": False,
        "streams_count": 0,
        "consumers_count": 0,
    }
    mock_nats_client.account_info.assert_called_once()


@pytest.mark.anyio
async def test_check_jetstream_exception(
    mock_nats_client,  # pylint: disable=redefined-outer-name
):
    processor = NatsEventsProcessor(mock_nats_client)
    mock_nats_client.account_info.side_effect = Exception("Test exception")

    result = await processor.check_jetstream()

    assert result == {"is_working": False}
    mock_nats_client.account_info.assert_called_once()
