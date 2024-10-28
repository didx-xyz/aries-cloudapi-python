from unittest.mock import AsyncMock, patch

import pytest
from app.models.wallet import DIDCreate
from aries_cloudcontroller import DIDCreate as AcapyDIDCreate
from aries_cloudcontroller.exceptions import (
    ApiException,
    BadRequestException,
    NotFoundException,
)

from app.routes.wallet.dids import create_did


@pytest.mark.anyio
@pytest.mark.parametrize(
    "request_body, create_body",
    [
        (None, None),
        (
            DIDCreate(method="key"),
            AcapyDIDCreate(method="key", options={"key_type": "ed25519"}),
        ),
        (
            DIDCreate(method="sov"),
            AcapyDIDCreate(method="sov", options={"key_type": "ed25519"}),
        ),
    ],
)
async def test_create_did_success(request_body, create_body):
    mock_aries_controller = AsyncMock()
    mock_create_did = AsyncMock()

    with patch(
        "app.routes.wallet.dids.client_from_auth"
    ) as mock_client_from_auth, patch(
        "app.services.acapy_wallet.create_did", mock_create_did
    ):
        # Configure client_from_auth to return our mocked aries_controller on enter
        mock_client_from_auth.return_value.__aenter__.return_value = (
            mock_aries_controller
        )

        await create_did(did_create=request_body, auth="mocked_auth")

        mock_create_did.assert_awaited_once_with(
            did_create=create_body, controller=mock_aries_controller
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
async def test_create_did_fail_acapy_error(
    exception_class, expected_status_code, expected_detail
):
    mock_aries_controller = AsyncMock()
    mock_create_did = AsyncMock(
        side_effect=exception_class(status=expected_status_code, reason=expected_detail)
    )

    with patch(
        "app.routes.wallet.dids.client_from_auth"
    ) as mock_client_from_auth, pytest.raises(
        exception_class, match=expected_detail
    ) as exc, patch(
        "app.services.acapy_wallet.create_did", mock_create_did
    ):
        # Configure client_from_auth to return our mocked aries_controller on enter
        mock_client_from_auth.return_value.__aenter__.return_value = (
            mock_aries_controller
        )

        await create_did(auth="mocked_auth")

    assert exc.value.status == expected_status_code
