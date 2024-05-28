from unittest.mock import AsyncMock, patch

import pytest
from aries_cloudcontroller import ReceiveInvitationRequest
from aries_cloudcontroller.exceptions import (
    ApiException,
    BadRequestException,
    NotFoundException,
)
from fastapi import HTTPException

from app.models.connections import AcceptInvitation
from app.routes.connections import accept_invitation
from shared.models.connection_record import Connection

test_alias = "Test Alias"
accept_invitation_body = AcceptInvitation(
    alias=test_alias,
    invitation=ReceiveInvitationRequest(),
)
accepted_connection = Connection(
    connection_id="some_connection_id",
    state="completed",
    alias=test_alias,
)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "body, expected_alias",
    [
        (accept_invitation_body, test_alias),
        (AcceptInvitation(invitation=ReceiveInvitationRequest()), None),
    ],
)
async def test_accept_invitation_success(body, expected_alias):
    mock_aries_controller = AsyncMock()
    mock_aries_controller.connection.receive_invitation = AsyncMock(
        return_value=accepted_connection
    )

    with patch(
        "app.routes.connections.client_from_auth"
    ) as mock_client_from_auth, patch(
        "app.routes.connections.conn_record_to_connection",
        return_value=accepted_connection,
    ):
        # Configure client_from_auth to return our mocked aries_controller on enter
        mock_client_from_auth.return_value.__aenter__.return_value = (
            mock_aries_controller
        )

        response = await accept_invitation(body=body, auth="mocked_auth")

        assert response == accepted_connection

        mock_aries_controller.connection.receive_invitation.assert_awaited_once_with(
            body=body.invitation,
            auto_accept=True,
            alias=expected_alias,
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "exception_class, expected_status_code, expected_detail",
    [
        (BadRequestException, 400, "Bad request"),
        (NotFoundException, 404, "Not found"),
        (ApiException, 500, "Internal Server Error"),
    ],
)
async def test_accept_invitation_fail_acapy_error(
    exception_class, expected_status_code, expected_detail
):
    mock_aries_controller = AsyncMock()
    mock_aries_controller.connection.receive_invitation = AsyncMock(
        side_effect=exception_class(status=expected_status_code, reason=expected_detail)
    )

    with patch(
        "app.routes.connections.client_from_auth"
    ) as mock_client_from_auth, pytest.raises(
        HTTPException, match=expected_detail
    ) as exc, patch(
        "app.routes.connections.conn_record_to_connection"
    ):
        # Configure client_from_auth to return our mocked aries_controller on enter
        mock_client_from_auth.return_value.__aenter__.return_value = (
            mock_aries_controller
        )

        await accept_invitation(body=accept_invitation_body, auth="mocked_auth")

    assert exc.value.status_code == expected_status_code
