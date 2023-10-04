from aiohttp import ClientResponseError
import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    ConnectionMetadata,
    ConnRecord,
    InvitationCreateRequest,
    InvitationMessage,
    InvitationRecord,
)
from assertpy import assert_that
from mockito import verify, when

from app.event_handling.sse_listener import SseListener
from app.exceptions.cloud_api_error import CloudApiException
from app.services import onboarding
from app.services.acapy_wallet import Did
from app.services.onboarding import acapy_ledger, acapy_wallet
from app.tests.util.mock import to_async
from shared.util.mock_agent_controller import get_mock_agent_controller


@pytest.mark.anyio
async def test_onboard_issuer_public_did_exists(
    mock_agent_controller: AcaPyClient,
):
    when(acapy_wallet).get_public_did(controller=mock_agent_controller).thenReturn(
        to_async(
            Did(
                did="WgWxqztrNooG92RXvxSTWv",
                verkey="WgWxqztrNooG92RXvxSTWvWgWxqztrNooG92RXvxSTWv",
            )
        )
    )

    endorser_controller = get_mock_agent_controller()

    when(endorser_controller.out_of_band).create_invitation(...).thenReturn(
        InvitationRecord(invitation=InvitationMessage())
    )
    when(mock_agent_controller.out_of_band).receive_invitation(...).thenReturn(
        ConnRecord()
    )

    when(acapy_wallet).get_public_did(controller=endorser_controller).thenReturn(
        Did(did="EndorserController", verkey="EndorserVerkey")
    )

    when(mock_agent_controller.endorse_transaction).set_endorser_role(...).thenReturn(
        None
    )
    when(endorser_controller.endorse_transaction).set_endorser_role(...).thenReturn(
        None
    )
    when(mock_agent_controller.endorse_transaction).set_endorser_info(...).thenReturn(
        None
    )

    # Mock event listeners
    when(onboarding).create_sse_listener(
        topic="connections", wallet_id="admin"
    ).thenReturn(MockSseListener(topic="connections", wallet_id="admin"))
    when(onboarding).create_sse_listener(
        topic="endorsements", wallet_id="admin"
    ).thenReturn(
        MockListenerEndorserConnectionId(topic="endorsements", wallet_id="admin")
    )

    invitation_url = "https://invitation.com"

    when(mock_agent_controller.out_of_band).create_invitation(...).thenReturn(
        to_async(
            InvitationRecord(
                invitation_url=invitation_url,
            )
        )
    )

    onboard_result = await onboarding.onboard_issuer(
        name="issuer_name",
        endorser_controller=endorser_controller,
        issuer_controller=mock_agent_controller,
        issuer_wallet_id="issuer_wallet_id",
    )

    assert_that(onboard_result).has_did("did:sov:WgWxqztrNooG92RXvxSTWv")


@pytest.mark.anyio
async def test_onboard_issuer_no_public_did(
    mock_agent_controller: AcaPyClient,
):
    endorser_controller = get_mock_agent_controller()
    endorser_did = "EndorserDid"

    when(acapy_wallet).get_public_did(controller=mock_agent_controller).thenRaise(
        CloudApiException(detail="Error")
    )
    when(acapy_wallet).get_public_did(controller=endorser_controller).thenReturn(
        to_async(Did(did=endorser_did, verkey="EndorserVerkey"))
    )

    when(endorser_controller.out_of_band).create_invitation(...).thenReturn(
        to_async(InvitationRecord(invitation=InvitationMessage()))
    )

    # Mock event listeners
    when(onboarding).create_sse_listener(
        topic="connections", wallet_id="admin"
    ).thenReturn(
        MockListenerEndorserConnectionId(topic="connections", wallet_id="admin")
    )
    when(onboarding).create_sse_listener(
        topic="endorsements", wallet_id="admin"
    ).thenReturn(MockListenerRequestReceived(topic="endorsements", wallet_id="admin"))

    # Mock responses
    when(mock_agent_controller.out_of_band).receive_invitation(...).thenReturn(
        to_async(ConnRecord())
    )
    when(mock_agent_controller.endorse_transaction).set_endorser_role(...).thenReturn(
        to_async()
    )
    # Mock the assert_connection_metadata methods
    when(endorser_controller.connection).get_metadata(...).thenReturn(
        to_async(
            ConnectionMetadata(
                results={
                    "transaction_jobs": {
                        "transaction_my_job": "TRANSACTION_ENDORSER",
                    },
                }
            )
        )
    )

    when(endorser_controller.endorse_transaction).set_endorser_role(...).thenReturn(
        to_async()
    )
    when(mock_agent_controller.endorse_transaction).set_endorser_info(...).thenReturn(
        to_async()
    )

    # Expanding the test scenario: we want to ensure that the coroutine is successfully retried in the
    # assert method after failing. We also need to mock `when(mock_agent_controller.connection).get_metadata`
    # to return different results for each assert call. So, create a counter iterable + method to simulate the
    # first assert_author_role_set check succeeding, then the assert_endorser_info_set call failing, and then succeeding

    call_counter = iter([0, 1, 2])

    async def mock_get_metadata_side_effect(*args, **kwargs):
        call_num = next(call_counter)

        # On the first call, it is for the assert_author_role_set method
        if call_num == 0:
            return ConnectionMetadata(
                results={
                    "transaction_jobs": {
                        "transaction_my_job": "TRANSACTION_AUTHOR",
                        "transaction_their_job": "TRANSACTION_ENDORSER",
                    },
                }
            )

        # On this call, raise the exception
        if call_num == 1:
            # Mocking the ClientResponseError to always return an exception instance without arguments
            class MockClientResponseError(ClientResponseError):
                def __init__(self):
                    pass

            raise MockClientResponseError

        # On this call, return a successful response for assert_endorser_info_set
        else:
            return ConnectionMetadata(
                results={
                    "transaction_jobs": {
                        "transaction_my_job": "TRANSACTION_AUTHOR",
                        "transaction_their_job": "TRANSACTION_ENDORSER",
                    },
                    "endorser_info": {"endorser_did": endorser_did},
                }
            )

    when(mock_agent_controller.connection).get_metadata(...).thenAnswer(
        mock_get_metadata_side_effect
    )

    when(acapy_wallet).create_did(mock_agent_controller).thenReturn(
        to_async(
            Did(
                did="WgWxqztrNooG92RXvxSTWv",
                verkey="WgWxqztrNooG92RXvxSTWvWgWxqztrNooG92RXvxSTWv",
            )
        )
    )
    when(acapy_ledger).register_nym_on_ledger(...).thenReturn(to_async())
    when(acapy_ledger).accept_taa_if_required(...).thenReturn(to_async())
    when(acapy_wallet).set_public_did(...).thenReturn(to_async())
    when(endorser_controller.endorse_transaction).endorse_transaction(...).thenReturn(
        to_async()
    )

    # Create an invitation as well
    invitation_url = "https://invitation.com"
    when(mock_agent_controller.out_of_band).create_invitation(...).thenReturn(
        to_async(
            InvitationRecord(
                invitation_url=invitation_url,
            )
        )
    )

    onboard_result = await onboarding.onboard_issuer(
        name="issuer_name",
        endorser_controller=endorser_controller,
        issuer_controller=mock_agent_controller,
        issuer_wallet_id="issuer_wallet_id",
    )

    assert_that(onboard_result).has_did("did:sov:WgWxqztrNooG92RXvxSTWv")
    verify(acapy_wallet).create_did(mock_agent_controller)
    verify(acapy_ledger).register_nym_on_ledger(
        endorser_controller,
        did="WgWxqztrNooG92RXvxSTWv",
        verkey="WgWxqztrNooG92RXvxSTWvWgWxqztrNooG92RXvxSTWv",
        alias="issuer_name",
    )
    verify(acapy_ledger).accept_taa_if_required(mock_agent_controller)
    verify(acapy_wallet).set_public_did(
        mock_agent_controller,
        did="WgWxqztrNooG92RXvxSTWv",
        create_transaction_for_endorser=True,
    )


@pytest.mark.anyio
async def test_onboard_verifier_public_did_exists(mock_agent_controller: AcaPyClient):
    when(acapy_wallet).get_public_did(controller=mock_agent_controller).thenReturn(
        to_async(
            Did(
                did="WgWxqztrNooG92RXvxSTWv",
                verkey="WgWxqztrNooG92RXvxSTWvWgWxqztrNooG92RXvxSTWv",
            )
        )
    )

    onboard_result = await onboarding.onboard_verifier(
        name="verifier_name", verifier_controller=mock_agent_controller
    )

    assert_that(onboard_result).has_did("did:sov:WgWxqztrNooG92RXvxSTWv")
    verify(acapy_wallet).get_public_did(controller=mock_agent_controller)


@pytest.mark.anyio
async def test_onboard_verifier_no_public_did(mock_agent_controller: AcaPyClient):
    when(acapy_wallet).get_public_did(controller=mock_agent_controller).thenRaise(
        CloudApiException(detail="No public did found")
    )

    did_key = "did:key:123"
    invitation_url = "https://invitation.com"

    when(mock_agent_controller.out_of_band).create_invitation(...).thenReturn(
        to_async(
            InvitationRecord(
                invitation_url=invitation_url,
                invitation=InvitationMessage(services=[{"recipientKeys": [did_key]}]),
            )
        )
    )

    onboard_result = await onboarding.onboard_verifier(
        name="verifier_name", verifier_controller=mock_agent_controller
    )

    assert_that(onboard_result).has_did(did_key)
    assert_that(onboard_result).has_didcomm_invitation(invitation_url)
    verify(mock_agent_controller.out_of_band).create_invitation(
        auto_accept=True,
        multi_use=True,
        body=InvitationCreateRequest(
            use_public_did=False,
            alias="Trust Registry verifier_name",
            handshake_protocols=["https://didcomm.org/didexchange/1.0"],
        ),
    )


@pytest.mark.anyio
async def test_onboard_verifier_no_recipient_keys(mock_agent_controller: AcaPyClient):
    when(acapy_wallet).get_public_did(controller=mock_agent_controller).thenRaise(
        CloudApiException(detail="No public did found")
    )
    when(mock_agent_controller.out_of_band).create_invitation(...).thenReturn(
        to_async(
            InvitationRecord(
                invitation=InvitationMessage(services=[{"recipientKeys": []}]),
            )
        )
    )

    with pytest.raises(CloudApiException):
        await onboarding.onboard_verifier(
            name="verifier_name", verifier_controller=mock_agent_controller
        )


class MockSseListener(SseListener):
    async def wait_for_event(self, field, field_id, desired_state, timeout: int = 150):
        pass


class MockListenerEndorserConnectionId(MockSseListener):
    async def wait_for_event(self, field, field_id, desired_state, timeout: int = 150):
        return {"connection_id": "endorser_connection_id"}


class MockListenerRequestReceived(MockSseListener):
    async def wait_for_state(self, desired_state, timeout: int = 150):
        return {"state": "request-received", "transaction_id": "abcde"}
