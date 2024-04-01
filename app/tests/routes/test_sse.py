from unittest.mock import Mock, patch

import pytest

from app.routes.sse import (
    get_sse_subscribe_event_with_field_and_state,
    get_sse_subscribe_event_with_state,
    get_sse_subscribe_stream_with_fields,
    get_sse_subscribe_wallet,
    get_sse_subscribe_wallet_topic,
)

wallet_id = "some_wallet"
group_id = "some_group_id"
topic = "some_topic"
field = "some_field"
field_id = "some_field_id"
state = "some_state"


@pytest.fixture()
def mock_request():
    return Mock()


@pytest.fixture()
def mock_auth():
    return Mock()


@pytest.fixture()
def mock_verify_wallet_access():
    with patch("app.routes.sse.verify_wallet_access", new=Mock()) as mocked:
        yield mocked


@pytest.mark.anyio
async def test_get_sse_subscribe_wallet(
    mock_request,  # pylint: disable=redefined-outer-name
    mock_auth,  # pylint: disable=redefined-outer-name
    mock_verify_wallet_access,  # pylint: disable=redefined-outer-name
):
    # Mock sse_subscribe_wallet function to not actually attempt to connect to an SSE stream
    sse_subscribe_wallet_mock = Mock()

    with patch("app.routes.sse.sse_subscribe_wallet", new=sse_subscribe_wallet_mock):
        # Call the route handler function
        response = await get_sse_subscribe_wallet(
            request=mock_request,
            wallet_id=wallet_id,
            group_id=group_id,
            auth=mock_auth,
        )

    assert response.media_type == "text/event-stream"

    # Assert that verify_wallet_access and sse_subscribe_wallet were called with the correct parameters
    mock_verify_wallet_access.assert_called_with(mock_auth, wallet_id)
    sse_subscribe_wallet_mock.assert_called_with(
        request=mock_request,
        group_id=group_id,
        wallet_id=wallet_id,
    )


@pytest.mark.anyio
async def test_get_sse_subscribe_wallet_topic(
    mock_request,  # pylint: disable=redefined-outer-name
    mock_auth,  # pylint: disable=redefined-outer-name
    mock_verify_wallet_access,  # pylint: disable=redefined-outer-name
):
    # Mock sse_subscribe_wallet_topic function to not actually attempt to connect to an SSE stream
    sse_subscribe_wallet_topic_mock = Mock()

    with patch(
        "app.routes.sse.sse_subscribe_wallet_topic", new=sse_subscribe_wallet_topic_mock
    ):
        # Call the route handler function
        response = await get_sse_subscribe_wallet_topic(
            request=mock_request,
            wallet_id=wallet_id,
            group_id=group_id,
            topic=topic,
            auth=mock_auth,
        )

    assert response.media_type == "text/event-stream"

    # Assert that verify_wallet_access and sse_subscribe_wallet_topic were called with the correct parameters
    mock_verify_wallet_access.assert_called_with(mock_auth, wallet_id)
    sse_subscribe_wallet_topic_mock.assert_called_with(
        request=mock_request,
        group_id=group_id,
        topic=topic,
        wallet_id=wallet_id,
    )


@pytest.mark.anyio
async def test_get_sse_subscribe_event_with_state(
    mock_request,  # pylint: disable=redefined-outer-name
    mock_auth,  # pylint: disable=redefined-outer-name
    mock_verify_wallet_access,  # pylint: disable=redefined-outer-name
):
    # Mock sse_subscribe_event_with_state function to not actually attempt to connect to an SSE stream
    sse_subscribe_event_with_state_mock = Mock()

    with patch(
        "app.routes.sse.sse_subscribe_event_with_state",
        new=sse_subscribe_event_with_state_mock,
    ):
        # Call the route handler function
        response = await get_sse_subscribe_event_with_state(
            request=mock_request,
            wallet_id=wallet_id,
            group_id=group_id,
            topic=topic,
            desired_state=state,
            auth=mock_auth,
        )

    assert response.media_type == "text/event-stream"

    # Assert that verify_wallet_access and sse_subscribe_event_with_state were called with the correct parameters
    mock_verify_wallet_access.assert_called_with(mock_auth, wallet_id)
    sse_subscribe_event_with_state_mock.assert_called_with(
        request=mock_request,
        wallet_id=wallet_id,
        group_id=group_id,
        topic=topic,
        desired_state=state,
    )


@pytest.mark.anyio
async def test_get_sse_subscribe_stream_with_fields(
    mock_request,  # pylint: disable=redefined-outer-name
    mock_auth,  # pylint: disable=redefined-outer-name
    mock_verify_wallet_access,  # pylint: disable=redefined-outer-name
):
    # Mock sse_subscribe_stream_with_fields function to not actually attempt to connect to an SSE stream
    sse_subscribe_stream_with_fields_mock = Mock()

    with patch(
        "app.routes.sse.sse_subscribe_stream_with_fields",
        new=sse_subscribe_stream_with_fields_mock,
    ):
        # Call the route handler function
        response = await get_sse_subscribe_stream_with_fields(
            request=mock_request,
            wallet_id=wallet_id,
            group_id=group_id,
            topic=topic,
            field=field,
            field_id=field_id,
            auth=mock_auth,
        )

    assert response.media_type == "text/event-stream"

    # Assert that verify_wallet_access and sse_subscribe_stream_with_fields were called with the correct parameters
    mock_verify_wallet_access.assert_called_with(mock_auth, wallet_id)
    sse_subscribe_stream_with_fields_mock.assert_called_with(
        request=mock_request,
        wallet_id=wallet_id,
        group_id=group_id,
        topic=topic,
        field=field,
        field_id=field_id,
    )


@pytest.mark.anyio
async def test_get_sse_subscribe_event_with_field_and_state(
    mock_request,  # pylint: disable=redefined-outer-name
    mock_auth,  # pylint: disable=redefined-outer-name
    mock_verify_wallet_access,  # pylint: disable=redefined-outer-name
):
    # Mock sse_subscribe_event_with_field_and_state function to not actually attempt to connect to an SSE stream
    sse_subscribe_event_with_field_and_state_mock = Mock()

    with patch(
        "app.routes.sse.sse_subscribe_event_with_field_and_state",
        new=sse_subscribe_event_with_field_and_state_mock,
    ):
        # Call the route handler function
        response = await get_sse_subscribe_event_with_field_and_state(
            request=mock_request,
            wallet_id=wallet_id,
            group_id=group_id,
            topic=topic,
            field=field,
            field_id=field_id,
            desired_state=state,
            auth=mock_auth,
        )

    assert response.media_type == "text/event-stream"

    # Assert that verify_wallet_access and sse_subscribe_event_with_field_and_state called with the correct parameters
    mock_verify_wallet_access.assert_called_with(mock_auth, wallet_id)
    sse_subscribe_event_with_field_and_state_mock.assert_called_with(
        request=mock_request,
        wallet_id=wallet_id,
        group_id=group_id,
        topic=topic,
        field=field,
        field_id=field_id,
        desired_state=state,
    )
