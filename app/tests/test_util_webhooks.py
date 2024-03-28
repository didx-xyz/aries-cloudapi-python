from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import HTTPError

from app.tests.util.webhooks import check_webhook_state

# pylint: disable=redefined-outer-name


@pytest.fixture
def mock_wallet_id(mocker):
    return mocker.patch(
        "app.tests.util.webhooks.get_wallet_id_from_async_client",
        return_value="wallet_id",
    )


@pytest.fixture
def mock_sse_listener(mocker):
    mock_listener = AsyncMock()
    mocker.patch("app.tests.util.webhooks.SseListener", return_value=mock_listener)
    return mock_listener


@pytest.mark.anyio
async def test_check_webhook_state_wait_for_event_success(
    mock_wallet_id,  # pylint: disable=unused-argument
    mock_sse_listener,
):
    client = MagicMock()
    topic = "connections"
    state = "desired_state"
    filter_map = {"field": "field_id"}

    expected_event = {"event": "details", "state": state}
    mock_sse_listener.wait_for_event.return_value = expected_event

    result = await check_webhook_state(client, topic, state, filter_map)

    assert result == expected_event
    mock_sse_listener.wait_for_event.assert_awaited_once_with(
        field="field",
        field_id="field_id",
        desired_state=state,
        timeout=60,
        lookback_time=1,
    )


@pytest.mark.anyio
async def test_check_webhook_state_wait_for_event_success_after_retry(
    mock_wallet_id,  # pylint: disable=unused-argument
    mock_sse_listener,
):
    client = MagicMock()
    topic = "some_topic"
    state = "desired_state"
    filter_map = {"field": "field_id"}

    expected_event = {"event": "details", "state": state}
    mock_sse_listener.wait_for_event.side_effect = [HTTPError(""), expected_event]

    result = await check_webhook_state(client, topic, state, filter_map, delay=0.01)

    assert result == expected_event
    assert (
        mock_sse_listener.wait_for_event.call_count == 2
    ), "Should have retried once after HTTPError"


@pytest.mark.anyio
async def test_check_webhook_state_wait_for_event_fails_after_max_retries(
    mock_wallet_id,  # pylint: disable=unused-argument
    mock_sse_listener,
):
    client = MagicMock()
    topic = "some_topic"
    state = "desired_state"
    filter_map = {"field": "field_id"}

    mock_sse_listener.wait_for_event.side_effect = HTTPError("")

    with pytest.raises(HTTPError):
        await check_webhook_state(client, topic, state, filter_map, delay=0.01)

    assert (
        mock_sse_listener.wait_for_event.call_count == 2
    ), "Should have retried the max number of times"


@pytest.mark.anyio
async def test_check_webhook_state_wait_for_state_success(
    mock_wallet_id,  # pylint: disable=unused-argument
    mock_sse_listener,
):
    client = MagicMock()
    topic = "connections"
    state = "desired_state"

    expected_event = {"event": "details", "state": state}
    mock_sse_listener.wait_for_state.return_value = expected_event

    result = await check_webhook_state(client, topic, state)

    assert result == expected_event
    mock_sse_listener.wait_for_state.assert_awaited_once_with(
        desired_state=state,
        timeout=60,
        lookback_time=1,
    )


@pytest.mark.anyio
async def test_check_webhook_state_wait_for_state_success_after_retry(
    mock_wallet_id,  # pylint: disable=unused-argument
    mock_sse_listener,
):
    client = MagicMock()
    topic = "some_topic"
    state = "desired_state"

    expected_event = {"event": "details", "state": state}
    mock_sse_listener.wait_for_state.side_effect = [HTTPError(""), expected_event]

    result = await check_webhook_state(client, topic, state, delay=0.01)

    assert result == expected_event
    assert (
        mock_sse_listener.wait_for_state.call_count == 2
    ), "Should have retried once after HTTPError"


@pytest.mark.anyio
async def test_check_webhook_state_wait_for_state_fails_after_max_retries(
    mock_wallet_id,  # pylint: disable=unused-argument
    mock_sse_listener,
):
    client = MagicMock()
    topic = "some_topic"
    state = "desired_state"

    mock_sse_listener.wait_for_state.side_effect = HTTPError("")

    with pytest.raises(HTTPError):
        await check_webhook_state(client, topic, state, delay=0.01)

    assert (
        mock_sse_listener.wait_for_state.call_count == 2
    ), "Should have retried the max number of times"
