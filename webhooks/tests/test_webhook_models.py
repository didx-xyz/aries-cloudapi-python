from typing import Dict, List

from shared.models.connection_record import Connection
from shared.models.credential_exchange import CredentialExchange
from shared.models.endorsement import Endorsement
from shared.models.presentation_exchange import PresentationExchange
from webhooks.models import (
    AcaPyWebhookEvent,
    BasicMessage,
    IssuerCredRevRecord,
    IssuerRevRegRecord,
    OobRecord,
    WebhookEventPayloadType,
)
from webhooks.models.conversions import acapy_to_cloudapi_event
from webhooks.models.topic_payloads import CredExRecordIndy, CredExRecordLDProof

acapy_webhook = AcaPyWebhookEvent(
    wallet_id="test_wallet",
    topic="test_topic",
    origin="test_origin",
    acapy_topic="test_topic",
    payload={},
)

basic_message_event_payload = {
    "connection_id": "123456780",
    "content": "Your hovercraft is full of eels.",
    "message_id": "123456780",
    "sent_time": "2019-01-15 18:42:01Z",
    "state": "received",
}

connection_event_payload = {
    "accept": "auto",
    "alias": "faber_AOTMK",
    "connection_id": "d4e96d60-0a73-4a1f-a1b6-6132358ddcbd",
    "connection_protocol": "didexchange/1.0",
    "created_at": "2024-03-05T10:51:55.794761Z",
    "error_msg": "x",
    "invitation_key": "5GRbkFkAh1mcgLF2CnXWupiUEo3kxzS7Tk7P5rU5FNmv",
    "invitation_mode": "once",
    "invitation_msg_id": "f042f042-4997-45ab-bbfe-811f5e751717",
    "my_did": "Rt4pxGi1Fde8V89D28XDTJ",
    "request_id": "42878091-ab09-4fff-b128-d42f7951f41e",
    "rfc23_state": "invitation-sent",
    "state": "invitation",
    "their_did": "8pxjUdsobm4w8X2ASWQtrR",
    "their_label": "Governance",
    "their_public_did": "8pxjUdsobm4w8X2ASWQtrR",
    "their_role": "inviter",
    "updated_at": "2024-03-05T10:51:55.794761Z",
}

endorsement_event_payload = {
    "state": "request_received",
    "created_at": "2024-03-05T10:55:28.438672Z",
    "updated_at": "2024-03-05T10:55:28.438672Z",
    "trace": False,
    "transaction_id": "88c7ac0b-9555-4307-a657-5b840db3cea2",
    "_type": "http://didcomm.org/sign-attachment/%VER/signature-request",
    "signature_request": [
        {
            "context": "did:sov",
            "method": "add-signature",
            "signature_type": "<requested signature type>",
            "signer_goal_code": "aries.transaction.endorse",
            "author_goal_code": "aries.transaction.ledger.write",
        }
    ],
    "signature_response": [],
    "timing": {"expires_time": None},
    "formats": [
        {
            "attach_id": "901f18f2-5422-4b35-b468-85c4cd7fe320",
            "format": "dif/endorse-transaction/request@v1.0",
        }
    ],
    "messages_attach": [
        {
            "@id": "901f18f2-5422-4b35-b468-85c4cd7fe320",
            "mime-type": "application/json",
            "data": {
                "json": {
                    "endorser": "8pxjUdsobm4w8X2ASWQtrR",
                    "identifier": "9dTJaBsMhXvTzmau2vkauz",
                    "operation": {
                        "dest": "9dTJaBsMhXvTzmau2vkauz",
                        "raw": '{"endpoint":{"endpoint":"http://governance-multitenant-agent:3020","routingKeys":[]}}',
                        "type": "100",
                    },
                    "protocolVersion": 2,
                    "reqId": 1709636128406146415,
                    "signature": (
                        "4R8acvAFxS12pqZdTL38a7iz5kGvke2CF6bNWPDEBmSMSwHT3gVyG5Fue25kNEaK4ubwQe38dd37e3iWwkxMmBQh"
                    ),
                    "taaAcceptance": {
                        "mechanism": "service_agreement",
                        "taaDigest": "0be4d87dec17a7901cb8ba8bb4239ee34d4f6e08906f3dad81d1d052dccc078f",
                        "time": 1709596800,
                    },
                }
            },
        }
    ],
    "meta_data": {"context": {}, "processing": {}},
    "thread_id": "43f67f50-f962-42be-a617-94030214f54e",
    "connection_id": "7e13849a-e2a0-466b-a4fb-84312f26396a",
}

oob_event_payload = {
    "state": "await-response",
    "created_at": "2024-03-05T10:55:28.706611Z",
    "updated_at": "2024-03-05T10:55:28.706611Z",
    "trace": False,
    "oob_id": "0fcc29d0-bf73-4f24-9b16-4d68f1c00bc2",
    "invi_msg_id": "89945076-7ba5-4d74-92d8-8a891d2dbde6",
    "invitation": {
        "@type": "https://didcomm.org/out-of-band/1.1/invitation",
        "@id": "89945076-7ba5-4d74-92d8-8a891d2dbde6",
        "label": "faber_DTXJY",
        "handshake_protocols": ["https://didcomm.org/didexchange/1.0"],
        "services": [
            {
                "id": "#inline",
                "type": "did-communication",
                "recipientKeys": [
                    (
                        "did:key:z6MkiBY7si4p3mXYZWuz9jL9L2VKV1WtLh8oEnGhpAmj7NMX"
                        "#z6MkiBY7si4p3mXYZWuz9jL9L2VKV1WtLh8oEnGhpAmj7NMX"
                    )
                ],
                "serviceEndpoint": "http://governance-multitenant-agent:3020",
            }
        ],
    },
    "connection_id": "cca9ff6c-0bd9-4c6e-8538-2579b58202dc",
    "our_recipient_key": "4jH5HTpNiE35T25HUANJUvwKfSF2votSYmMmytoiC9a9",
    "role": "sender",
}

issue_credential_v1_0_event_payload = {
    "role": "issuer",
    "initiator": "self",
    "auto_offer": False,
    "auto_remove": True,
    "thread_id": "678e4f38-9452-498f-ad60-3176c95b429a",
    "state": "offer_sent",
    "credential_definition_id": "VDhakWxAru5YGvr2EEEWfp:3:CL:16:tag",
    "schema_id": "VmMUGgYqNoeMffPyhkhqep:2:test_schema:56.72.72",
    "created_at": "2024-03-06T20:26:16.551320Z",
    "updated_at": "2024-03-06T20:26:16.551320Z",
    "credential_exchange_id": "b4d4a8a4-ec27-4c0e-b46a-e67f9b5b0388",
}

issue_credential_v2_0_event_payload = {
    "role": "issuer",
    "initiator": "self",
    "auto_offer": False,
    "auto_remove": True,
    "thread_id": "8d1f6c59-8032-400a-a7d9-e5a9daf05f5f",
    "state": "offer-sent",
    "created_at": "2024-03-06T20:26:54.428898Z",
    "updated_at": "2024-03-06T20:26:54.428898Z",
    "cred_ex_id": "78d216c8-a210-4e6f-bbe8-d93180a88a2d",
}

issue_credential_v2_0_indy_event_payload = {
    "created_at": "2024-03-07T07:56:08.316204Z",
    "updated_at": "2024-03-07T07:56:08.316204Z",
    "cred_ex_indy_id": "281c2436-35bc-453a-bec8-771b5e95759b",
    "cred_ex_id": "de58b9ee-85e2-44fa-ad02-cd1c3e4d0f90",
    "cred_request_metadata": {
        "master_secret_blinding_data": {
            "v_prime": (
                "32121437961053510851105450867939422298894949696250264006383500"
                "3776797299324986415177511960624693819212228645094924810731959710972585052"
                "4470419898488248082401550132303097748931254851439395706967323261334226035"
                "8464427194114107824545472447094563563016520661946003061633136499010571040"
                "2679844330897668354868895253635394734956593778276927902482029253683558179"
                "2350833859362248871078658770747409479206073083612151194888016028722345660"
                "8107452388547383665429871078704483629869962953951236416854591921175660678"
                "3767404538087139093793690108053152151044125022619500610830430024415416288"
                "47408080571331708812337603757371271493486144633241542403216814484036"
            ),
            "vr_prime": None,
        },
        "nonce": "650900890204237446704340",
        "master_secret_name": "default",
    },
}

issue_credential_v2_0_ld_event_payload = {
    "created_at": "2024-03-07T07:54:42.278993Z",
    "updated_at": "2024-03-07T07:54:42.278993Z",
    "cred_ex_ld_proof_id": "d8ec9521-b48f-45ec-82a8-333a14c041ee",
    "cred_ex_id": "99fd311a-ec90-4b3e-ba30-a461dbae606b",
    "cred_id_stored": "642e52c9172a491286bad16b209936e7",
}

present_proof_v1_0_event_payload = {
    "connection_id": "e6c87053-e25e-4bee-bc23-048c7da43fbd",
    "role": "verifier",
    "initiator": "self",
    "auto_present": False,
    "auto_verify": True,
    "state": "request_sent",
    "thread_id": "dc7425cb-a260-490f-8c02-0c25ca1bb095",
    "trace": False,
    "created_at": "2024-03-07T07:40:20.148247Z",
    "updated_at": "2024-03-07T07:40:20.148247Z",
    "presentation_exchange_id": "550d3c83-fc62-4b48-9161-4c608530d159",
}

present_proof_v2_0_event_payload = {
    "role": "verifier",
    "initiator": "self",
    "auto_present": False,
    "auto_verify": True,
    "thread_id": "d57b9e74-c961-4b43-b2a4-a77edf5ffd53",
    "state": "request-sent",
    "trace": False,
    "created_at": "2024-03-07T07:40:27.640682Z",
    "updated_at": "2024-03-07T07:40:27.640682Z",
    "pres_ex_id": "e4f0dad1-9c3e-47d2-9e8f-b70b3303b3ec",
}

revocation_event_payload = {
    "state": "init",
    "created_at": "2024-03-05T10:55:35.542249Z",
    "updated_at": "2024-03-05T10:55:35.542249Z",
    "record_id": "2db7da9e-bf1e-47f7-b016-ab41b7bf4e4c",
    "cred_def_id": "9dTJaBsMhXvTzmau2vkauz:3:CL:13:VMOIP",
    "issuer_did": "9dTJaBsMhXvTzmau2vkauz",
    "max_cred_num": 32767,
    "revoc_def_type": "CL_ACCUM",
    "revoc_reg_id": (
        "9dTJaBsMhXvTzmau2vkauz:4:9dTJaBsMhXvTzmau2vkauz:3:CL:13:VMOIP:"
        "CL_ACCUM:2db7da9e-bf1e-47f7-b016-ab41b7bf4e4c"
    ),
    "pending_pub": [],
}

issuer_cred_rev_event_payload = {
    "state": "issued",
    "created_at": "2024-03-07T07:55:55.443663Z",
    "updated_at": "2024-03-07T07:55:55.443663Z",
    "record_id": "12658f33-cd4d-40fa-9adc-c31cb3ba6687",
    "cred_ex_id": "ceabcae9-ba61-4961-935e-6c98b2f5e754",
    "rev_reg_id": (
        "XRniRTaMU3mdMRkMrSvvmg:4:XRniRTaMU3mdMRkMrSvvmg:3:"
        "CL:25:tag:CL_ACCUM:5a2f9198-0114-48cb-a7a3-de6299919856"
    ),
    "cred_def_id": "XRniRTaMU3mdMRkMrSvvmg:3:CL:25:tag",
    "cred_rev_id": "1",
    "cred_ex_version": "1",
}


# Helper method to dynamically check every key in the payload against the model's attributes
def validate_result(
    result: WebhookEventPayloadType, input_payload: Dict[str, str], skip: List[str]
):
    print(f"{result=}")
    print(f"{input_payload=}")
    for key, value in input_payload.items():
        if key in skip:
            continue
        key = key.replace("@", "")  # for @type and @id fields
        assert hasattr(result, key), f"Model missing attribute for key {key}"
        assert getattr(result, key) == value, f"Mismatch on {key}"


def test_to_basic_message_model():
    event = acapy_webhook.model_copy(
        update={"topic": "basic-messages", "payload": basic_message_event_payload}
    )
    cloudapi_event = acapy_to_cloudapi_event(event)
    result = cloudapi_event.payload
    assert isinstance(result, BasicMessage)
    validate_result(result, basic_message_event_payload, skip=[])


def test_to_connections_model():
    unused_fields = ["accept", "request_id"]
    skip_fields = ["state", "rfc23_state"] + unused_fields
    event = acapy_webhook.model_copy(
        update={"topic": "connections", "payload": connection_event_payload}
    )
    cloudapi_event = acapy_to_cloudapi_event(event)
    result = cloudapi_event.payload
    assert isinstance(result, Connection)
    validate_result(result, connection_event_payload, skip=skip_fields)
    assert result.state == connection_event_payload["rfc23_state"]


def test_to_endorsement_model():
    event = acapy_webhook.model_copy(
        update={"topic": "endorsements", "payload": endorsement_event_payload}
    )
    cloudapi_event = acapy_to_cloudapi_event(event)
    result = cloudapi_event.payload
    assert isinstance(result, Endorsement)
    assert result.state == endorsement_event_payload["state"].replace("_", "-")
    assert result.transaction_id == endorsement_event_payload["transaction_id"]


def test_to_oob_model():
    event = acapy_webhook.model_copy(
        update={"topic": "oob", "payload": oob_event_payload}
    )
    cloudapi_event = acapy_to_cloudapi_event(event)
    result = cloudapi_event.payload
    assert isinstance(result, OobRecord)
    validate_result(result, oob_event_payload, skip=["invitation"])
    # and to account for nested model:
    validate_result(result.invitation, oob_event_payload["invitation"], skip=[])


def test_credential_model():
    # Fields purposefully not included in model
    unused_fields = ["initiator", "auto_offer", "auto_remove", "credential_exchange_id"]
    skip_fields = ["state"] + unused_fields

    ### V1
    event_v1 = acapy_webhook.model_copy(
        update={
            "topic": "credentials",
            "acapy_topic": "issue_credential",
            "payload": issue_credential_v1_0_event_payload,
        }
    )
    cloudapi_event_v1 = acapy_to_cloudapi_event(event_v1)

    result_v1 = cloudapi_event_v1.payload
    assert isinstance(result_v1, CredentialExchange)

    validate_result(result_v1, issue_credential_v1_0_event_payload, skip=skip_fields)

    # validate state separately
    modified_state = issue_credential_v1_0_event_payload["state"].replace("_", "-")
    assert result_v1.state == modified_state

    # validate modified credential_exchange_id
    cred_ex_id = issue_credential_v1_0_event_payload["credential_exchange_id"]
    modified_cred_ex_id = f"v1-{cred_ex_id}"
    assert result_v1.credential_exchange_id == modified_cred_ex_id

    ### V2
    event_v2 = acapy_webhook.model_copy(
        update={
            "topic": "credentials",
            "acapy_topic": "issue_credential_v2_0",
            "payload": issue_credential_v2_0_event_payload,
        }
    )
    cloudapi_event_v2 = acapy_to_cloudapi_event(event_v2)
    print(f"{event_v2=}")
    print(f"{cloudapi_event_v2=}")
    result_v2 = cloudapi_event_v2.payload
    assert isinstance(result_v2, CredentialExchange)

    skip_v2 = skip_fields + ["cred_ex_id"]
    validate_result(result_v2, issue_credential_v2_0_event_payload, skip=skip_v2)

    # validate state separately
    modified_state = issue_credential_v2_0_event_payload["state"].replace("_", "-")
    assert result_v2.state == modified_state

    # validate modified credential_exchange_id
    cred_ex_id = issue_credential_v2_0_event_payload["cred_ex_id"]
    modified_cred_ex_id = f"v2-{cred_ex_id}"
    assert result_v2.credential_exchange_id == modified_cred_ex_id


def test_credential_indy_model():
    event = acapy_webhook.model_copy(
        update={
            "topic": "credentials_indy",
            "payload": issue_credential_v2_0_indy_event_payload,
        }
    )
    cloudapi_event = acapy_to_cloudapi_event(event)
    result = cloudapi_event.payload
    assert isinstance(result, CredExRecordIndy)
    validate_result(result, issue_credential_v2_0_indy_event_payload, skip=[])


def test_credential_ld_model():
    event = acapy_webhook.model_copy(
        update={
            "topic": "credentials_ld",
            "payload": issue_credential_v2_0_ld_event_payload,
        }
    )
    cloudapi_event = acapy_to_cloudapi_event(event)
    result = cloudapi_event.payload
    assert isinstance(result, CredExRecordLDProof)
    validate_result(result, issue_credential_v2_0_ld_event_payload, skip=[])


def test_proof_model():
    # Fields purposefully not included in model
    unused_fields = [
        "initiator",
        "auto_present",
        "auto_verify",
        "trace",
        "presentation_exchange_id",
    ]
    skip_fields = ["state"] + unused_fields

    ### V1
    event_v1 = acapy_webhook.model_copy(
        update={
            "topic": "proofs",
            "acapy_topic": "present_proof",
            "payload": present_proof_v1_0_event_payload,
        }
    )
    cloudapi_event_v1 = acapy_to_cloudapi_event(event_v1)

    result_v1 = cloudapi_event_v1.payload
    assert isinstance(result_v1, PresentationExchange)

    validate_result(result_v1, present_proof_v1_0_event_payload, skip=skip_fields)

    # validate state separately
    modified_state = present_proof_v1_0_event_payload["state"].replace("_", "-")
    assert result_v1.state == modified_state

    # validate modified presentation_exchange_id
    pres_ex_id = present_proof_v1_0_event_payload["presentation_exchange_id"]
    modified_pres_ex_id = f"v1-{pres_ex_id}"
    assert result_v1.proof_id == modified_pres_ex_id

    ### V2
    event_v2 = acapy_webhook.model_copy(
        update={
            "topic": "proofs",
            "acapy_topic": "present_proof_v2_0",
            "payload": present_proof_v2_0_event_payload,
        }
    )
    cloudapi_event_v2 = acapy_to_cloudapi_event(event_v2)

    result_v2 = cloudapi_event_v2.payload
    assert isinstance(result_v2, PresentationExchange)

    skip_v2 = skip_fields + ["pres_ex_id"]
    validate_result(result_v2, present_proof_v2_0_event_payload, skip=skip_v2)

    # validate state separately
    modified_state = present_proof_v2_0_event_payload["state"].replace("_", "-")
    assert result_v2.state == modified_state

    # validate modified presentation_exchange_id
    pres_ex_id = present_proof_v2_0_event_payload["pres_ex_id"]
    modified_pres_ex_id = f"v2-{pres_ex_id}"
    assert result_v2.proof_id == modified_pres_ex_id


def test_to_revocation_model():
    event = acapy_webhook.model_copy(
        update={"topic": "revocation", "payload": revocation_event_payload}
    )
    cloudapi_event = acapy_to_cloudapi_event(event)
    result = cloudapi_event.payload
    assert isinstance(result, IssuerRevRegRecord)
    validate_result(result, revocation_event_payload, skip=[])


def test_to_issuer_cred_rev_model():
    event = acapy_webhook.model_copy(
        update={"topic": "issuer_cred_rev", "payload": issuer_cred_rev_event_payload}
    )
    cloudapi_event = acapy_to_cloudapi_event(event)
    result = cloudapi_event.payload
    assert isinstance(result, IssuerCredRevRecord)
    validate_result(result, issuer_cred_rev_event_payload, skip=[])


# NB: No current webhook event example of a ProblemReport generated in our webhook logs
