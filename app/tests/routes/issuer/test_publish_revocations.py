import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from aries_cloudcontroller import TxnOrPublishRevocationsResult

from app.exceptions.cloudapi_exception import CloudApiException
from app.models.issuer import PublishRevocationsRequest
from app.routes.issuer import publish_revocations


@pytest.mark.anyio
async def test_publish_revocations_success():
    mock_aries_controller = AsyncMock()
    mock_publish_revocations = AsyncMock(
        return_value=TxnOrPublishRevocationsResult(
            txn={ #todo: reduce size or move out
                "state": "request_sent",
                "created_at": "2024-07-16T07:09:37.807261Z",
                "updated_at": "2024-07-16T07:09:37.812035Z",
                "trace": False,
                "transaction_id": "667f76bf-f950-4dd6-a2f2-b84a3b39b5e1",
                "_type": "https://didcomm.org/sign-attachment/1.0/signature-request",
                "signature_request": [
                    {
                        "context": "did:sov",
                        "method": "add-signature",
                        "signature_type": "default",
                        "signer_goal_code": "aries.transaction.endorse",
                        "author_goal_code": "aries.transaction.ledger.write",
                    }
                ],
                "signature_response": [],
                "timing": {"expires_time": None},
                "formats": [
                    {
                        "attach_id": "dbeb9942-fe14-4960-a242-cdc469495ee8",
                        "format": "dif/endorse-transaction/request@v1.0",
                    }
                ],
                "messages_attach": [
                    {
                        "@id": "dbeb9942-fe14-4960-a242-cdc469495ee8",
                        "mime-type": "application/json",
                        "data": {
                            "json": {
                                "endorser": "CYJnoJA7fDaz6hWoDP4nj7",
                                "identifier": "WYbzsbG3Nzx9ME3AC9poTD",
                                "operation": {
                                    "revocDefType": "CL_ACCUM",
                                    "revocRegDefId": "WYbzsbG3Nzx9ME3AC9poTD:4:WYbzsbG3Nzx9ME3AC9poTD:3:CL:8:Epic:CL_ACCUM:7f7d0e58-a868-41b2-ae7d-1c69a9309c9c",
                                    "type": "114",
                                    "value": {
                                        "accum": "...",
                                        "prevAccum": "...",
                                        "revoked": [7],
                                    },
                                },
                                "protocolVersion": 2,
                                "reqId": 1721113777802885400,
                                "signature": "3KtmzZt2WnQTWXqipPBmLJQMjLYmy7ve83QGD9VdRYeg3TMxzbxerDRnDsASKyqXjkZMYbzemwPgz7QgxUSfAU3f",
                                "taaAcceptance": {
                                    "mechanism": "service_agreement",
                                    "taaDigest": "0be4d87dec17a7901cb8ba8bb4239ee34d4f6e08906f3dad81d1d052dccc078f",
                                    "time": 1721088000,
                                },
                            }
                        },
                    }
                ],
                "meta_data": {"context": {}, "processing": {}},
                "connection_id": "64753329-ec71-4b19-b2e0-ee6c6e5a5cfd",
                "endorser_write_txn": False,
            }
        )
    )
    # mock_publish_revocations.return_value.txn.transaction_id = "transaction_id"

    mock_get_transaction = AsyncMock()

    with patch("app.routes.issuer.client_from_auth") as mock_client_from_auth, patch(
        "app.services.revocation_registry.publish_pending_revocations",
        mock_publish_revocations,
    ), patch(
        "app.routes.issuer.coroutine_with_retry_until_value", mock_get_transaction
    ):
        mock_client_from_auth.return_value.__aenter__.return_value = (
            mock_aries_controller
        )

        publish_request = PublishRevocationsRequest(
            revocation_registry_credential_map={}
        )

        await publish_revocations(publish_request=publish_request, auth="mocked_auth")

        mock_publish_revocations.assert_awaited_once_with(
            controller=mock_aries_controller, revocation_registry_credential_map={}
        )
        mock_get_transaction.assert_awaited_once()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "exception_class, expected_status_code, expected_detail",
    [
        (CloudApiException, 400, "Bad request"),
        (CloudApiException, 404, "Not found"),
        (CloudApiException, 500, "Internal Server Error"),
    ],
)
async def test_publish_revocations_fail_acapy_error(
    exception_class, expected_status_code, expected_detail
):
    mock_aries_controller = AsyncMock()
    mock_publish_revocations = AsyncMock(
        side_effect=exception_class(
            status_code=expected_status_code, detail=expected_detail
        )
    )

    with patch(
        "app.routes.issuer.client_from_auth"
    ) as mock_client_from_auth, pytest.raises(
        CloudApiException, match=expected_detail
    ) as exc, patch(
        "app.services.revocation_registry.publish_pending_revocations",
        mock_publish_revocations,
    ):
        mock_client_from_auth.return_value.__aenter__.return_value = (
            mock_aries_controller
        )

        publish_request = PublishRevocationsRequest(
            revocation_registry_credential_map={}
        )

        await publish_revocations(publish_request=publish_request, auth="mocked_auth")

    assert exc.value.status_code == expected_status_code


@pytest.mark.anyio
async def test_publish_revocations_fail_timeout():
    mock_aries_controller = AsyncMock()
    mock_publish_revocations = AsyncMock(spec=TxnOrPublishRevocationsResult)
    mock_publish_revocations.return_value.txn.transaction_id = "transaction_id"

    with patch(
        "app.routes.issuer.client_from_auth"
    ) as mock_client_from_auth, pytest.raises(
        CloudApiException,
        match="Timeout waiting for endorser to accept the revocations request.",
    ) as exc, patch(
        "app.services.revocation_registry.publish_pending_revocations",
        mock_publish_revocations,
    ), patch(
        "app.routes.issuer.coroutine_with_retry_until_value",
        AsyncMock(side_effect=asyncio.TimeoutError()),
    ):
        mock_client_from_auth.return_value.__aenter__.return_value = (
            mock_aries_controller
        )

        publish_request = PublishRevocationsRequest(
            revocation_registry_credential_map={}
        )

        await publish_revocations(publish_request=publish_request, auth="mocked_auth")

    assert exc.value.status_code == 504
