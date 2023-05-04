import pytest
from aries_cloudcontroller import (AcaPyClient, ConnRecord,
                                   InvitationCreateRequest, InvitationMessage,
                                   InvitationRecord, TransactionList,
                                   TransactionRecord)
from assertpy import assert_that
from asynctest import CoroutineMock, MagicMock
from mockito import verify, when

import app.admin.tenants.onboarding as onboarding
from app.admin.tenants.onboarding import acapy_ledger, acapy_wallet
from app.error.cloud_api_error import CloudApiException
from app.facades.acapy_wallet import Did
from app.listener import Listener
from tests.fixtures import get_mock_agent_controller
from tests.util.mock import get


@pytest.mark.asyncio
async def test_onboard_issuer_public_did_exists(
    mock_agent_controller: AcaPyClient,
):
    when(acapy_wallet).get_public_did(controller=mock_agent_controller).thenReturn(
        get(
            Did(
                did="WgWxqztrNooG92RXvxSTWv",
                verkey="WgWxqztrNooG92RXvxSTWvWgWxqztrNooG92RXvxSTWv",
            )
        )
    )

    endorser_controller = get_mock_agent_controller()

    when(endorser_controller.out_of_band).create_invitation(...).thenReturn(
        get(InvitationRecord(invitation=InvitationMessage()))
    )
    when(mock_agent_controller.out_of_band).receive_invitation(...).thenReturn(
        get(ConnRecord())
    )

    when(acapy_wallet).get_public_did(controller=endorser_controller).thenReturn(
        get(Did(did="EndorserController", verkey="EndorserVerkey"))
    )

    when(mock_agent_controller.endorse_transaction).set_endorser_role(...).thenReturn(
        get()
    )
    when(endorser_controller.endorse_transaction).set_endorser_role(...).thenReturn(
        get()
    )
    when(mock_agent_controller.endorse_transaction).set_endorser_info(...).thenReturn(
        get()
    )

    # Mock event listeners
    when(onboarding)._create_listener(
        topic="connections", wallet_id="admin"
    ).thenReturn(MockListener(topic="connections", wallet_id="admin"))
    when(onboarding)._create_listener(topic="endorsements", wallet_id="admin").thenReturn(
        MockListenerEndorserConnectionId(topic="endorsements", wallet_id="admin")
    )

    invitation_url = "https://invitation.com"

    when(mock_agent_controller.out_of_band).create_invitation(...).thenReturn(
        get(
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


@pytest.mark.asyncio
async def test_onboard_issuer_no_public_did(
    mock_agent_controller: AcaPyClient,
):
    endorser_controller = get_mock_agent_controller()

    when(acapy_wallet).get_public_did(controller=mock_agent_controller).thenRaise(
        CloudApiException(detail="Error")
    )
    when(acapy_wallet).create_did(mock_agent_controller).thenReturn(
        get(
            Did(
                did="WgWxqztrNooG92RXvxSTWv",
                verkey="WgWxqztrNooG92RXvxSTWvWgWxqztrNooG92RXvxSTWv",
            )
        )
    )

    when(acapy_ledger).register_nym_on_ledger(...).thenReturn(get())

    when(acapy_ledger).accept_taa_if_required(...).thenReturn(get())
    when(acapy_wallet).set_public_did(...).thenReturn(get())

    when(acapy_wallet).get_public_did(controller=endorser_controller).thenReturn(
        get(Did(did="EndorserController", verkey="EndorserVerkey"))
    )

    when(endorser_controller.out_of_band).create_invitation(...).thenReturn(
        get(InvitationRecord(invitation=InvitationMessage()))
    )
    when(mock_agent_controller.out_of_band).receive_invitation(...).thenReturn(
        get(ConnRecord())
    )

    when(mock_agent_controller.endorse_transaction).set_endorser_role(...).thenReturn(
        get()
    )
    when(endorser_controller.endorse_transaction).set_endorser_role(...).thenReturn(
        get()
    )
    when(mock_agent_controller.endorse_transaction).set_endorser_info(...).thenReturn(
        get()
    )

    # Mock event listeners
    when(onboarding)._create_listener(topic="connections", wallet_id="admin").thenReturn(
        MockListenerEndorserConnectionId(topic="connections", wallet_id="admin")
    )

    when(onboarding)._create_listener(topic="endorsements", wallet_id="admin").thenReturn(
        MockListenerRequestReceived(topic="endorsements", wallet_id="admin")
    )

    when(endorser_controller.endorse_transaction).get_records(...).thenReturn(
        get(
            TransactionList(
                results=[
                    TransactionRecord(
                        state="request-received",
                        transaction_id="abcde",
                        connection_id="endorser_connection_id",
                    ),
                    TransactionRecord(
                        state="request-received",
                        transaction_id="abcde",
                        connection_id="some_other_connection_id",
                    ),
                ]
            )
        )
    )
    when(endorser_controller.endorse_transaction).endorse_transaction(...).thenReturn(
        get()
    )
    invitation_url = "https://invitation.com"

    when(mock_agent_controller.out_of_band).create_invitation(...).thenReturn(
        get(
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


@pytest.mark.asyncio
async def test_onboard_verifier_public_did_exists(mock_agent_controller: AcaPyClient):
    when(acapy_wallet).get_public_did(controller=mock_agent_controller).thenReturn(
        get(
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


@pytest.mark.asyncio
async def test_onboard_verifier_no_public_did(mock_agent_controller: AcaPyClient):
    when(acapy_wallet).get_public_did(controller=mock_agent_controller).thenRaise(
        CloudApiException(detail="No public did found")
    )

    did_key = "did:key:123"
    invitation_url = "https://invitation.com"

    when(mock_agent_controller.out_of_band).create_invitation(...).thenReturn(
        get(
            InvitationRecord(
                invitation_url=invitation_url,
                invitation=InvitationMessage(
                    services=[{"recipientKeys": [did_key]}]),
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


@pytest.mark.asyncio
async def test_onboard_verifier_no_recipient_keys(mock_agent_controller: AcaPyClient):
    when(acapy_wallet).get_public_did(controller=mock_agent_controller).thenRaise(
        CloudApiException(detail="No public did found")
    )
    when(mock_agent_controller.out_of_band).create_invitation(...).thenReturn(
        get(
            InvitationRecord(
                invitation=InvitationMessage(services=[{"recipientKeys": []}]),
            )
        )
    )

    with pytest.raises(CloudApiException, match="Error creating invitation:"):
        await onboarding.onboard_verifier(
            name="verifier_name", verifier_controller=mock_agent_controller
        )


class MockListener(Listener):
    async def wait_for_filtered_event(self, filter_map: Dict[str, Any], timeout: float = 300):
        pass

    def stop(self):
        pass


class MockListenerEndorserConnectionId(MockListener):
    async def wait_for_filtered_event(self, filter_map: Dict[str, Any], timeout: float = 300):
        return {"connection_id": "endorser_connection_id"}


class MockListenerRequestReceived(MockListener):
    async def wait_for_filtered_event(self, filter_map: Dict[str, Any], timeout: float = 300):
        return {"state": "request-received", "transaction_id": "abcde"}
