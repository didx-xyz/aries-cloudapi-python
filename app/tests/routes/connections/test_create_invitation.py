from unittest.mock import AsyncMock, patch

import pytest
from aries_cloudcontroller import (
    ConnectionInvitation,
    CreateInvitationRequest,
    InvitationResult,
)
from aries_cloudcontroller.exceptions import (
    ApiException,
    BadRequestException,
    NotFoundException,
)
from fastapi import HTTPException

from app.models.connections import CreateInvitation
from app.routes.connections import create_invitation

test_alias = "Test Alias"
create_invitation_body = CreateInvitation(
    alias=test_alias,
    multi_use=False,
    use_public_did=False,
)
create_invitation_response = InvitationResult(
    connection_id="some_connection_id",
    invitation_url="http://example.com/invitation",
    invitation=ConnectionInvitation(),
)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "body, expected_alias, expected_multi_use, expected_use_public_did",
    [
        (None, None, False, False),
        (CreateInvitation(), None, False, False),
        (create_invitation_body, test_alias, False, False),
        (CreateInvitation(multi_use=True), None, True, False),
        (CreateInvitation(use_public_did=True), None, False, True),
    ],
)
async def test_create_invitation_success(
    body, expected_alias, expected_multi_use, expected_use_public_did
):
    mock_aries_controller = AsyncMock()
    mock_aries_controller.connection.create_invitation = AsyncMock(
        return_value=create_invitation_response
    )

    with patch("app.routes.connections.client_from_auth") as mock_client_from_auth:
        # Configure client_from_auth to return our mocked aries_controller on enter
        mock_client_from_auth.return_value.__aenter__.return_value = (
            mock_aries_controller
        )

        response = await create_invitation(body=body, auth="mocked_auth")

        assert response == create_invitation_response

        mock_aries_controller.connection.create_invitation.assert_awaited_once_with(
            alias=expected_alias,
            auto_accept=True,
            multi_use=expected_multi_use,
            public=expected_use_public_did,
            body=CreateInvitationRequest(),
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
async def test_create_invitation_fail_acapy_error(
    exception_class, expected_status_code, expected_detail
):
    mock_aries_controller = AsyncMock()
    mock_aries_controller.connection.create_invitation = AsyncMock(
        side_effect=exception_class(status=expected_status_code, reason=expected_detail)
    )

    with patch(
        "app.routes.connections.client_from_auth"
    ) as mock_client_from_auth, pytest.raises(
        HTTPException, match=expected_detail
    ) as exc:
        # Configure client_from_auth to return our mocked aries_controller on enter
        mock_client_from_auth.return_value.__aenter__.return_value = (
            mock_aries_controller
        )

        await create_invitation(body=create_invitation_body, auth="mocked_auth")

    assert exc.value.status_code == expected_status_code
