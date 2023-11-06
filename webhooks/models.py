from typing import Callable, Dict, Optional

from aries_cloudcontroller import (
    ConnRecord,
    IssuerCredRevRecord,
    IssuerRevRegRecord,
    OobRecord,
    V10CredentialExchange,
    V10PresentationExchange,
    V20CredExRecord,
    V20PresExRecord,
)

from shared.models.conversion import (
    conn_record_to_connection,
    credential_record_to_model_v1,
    credential_record_to_model_v2,
    presentation_record_to_model,
)
from shared.models.webhook_topics import (
    AcaPyWebhookEvent,
    CloudApiTopics,
    Connection,
    CredentialExchange,
    Endorsement,
    PresentationExchange,
)
from shared.models.webhook_topics.base import (
    BasicMessage,
    CloudApiWebhookEvent,
    ProblemReport,
    WebhookEventPayloadType,
)


def to_basic_message_model(event: AcaPyWebhookEvent) -> BasicMessage:
    return BasicMessage(**event.payload)


def to_connections_model(event: AcaPyWebhookEvent) -> Connection:
    conn_record = ConnRecord(**event.payload)
    conn_record = conn_record_to_connection(connection_record=conn_record)

    return conn_record


def to_endorsement_model(event: AcaPyWebhookEvent) -> Endorsement:
    if event.payload.get("state"):
        event.payload["state"] = event.payload["state"].replace("_", "-")
    return Endorsement(**event.payload)


def to_oob_model(event: AcaPyWebhookEvent) -> OobRecord:
    return OobRecord(**event.payload)


def to_revocation_model(event: AcaPyWebhookEvent) -> IssuerRevRegRecord:
    return IssuerRevRegRecord(**event.payload)


def to_issuer_cred_rev_model(event: AcaPyWebhookEvent) -> IssuerCredRevRecord:
    return IssuerCredRevRecord(**event.payload)


def to_problem_report_model(event: AcaPyWebhookEvent) -> ProblemReport:
    return ProblemReport(**event.payload)


def to_credential_model(event: AcaPyWebhookEvent) -> CredentialExchange:
    # v1
    if event.acapy_topic == "issue_credential":
        cred_exchange = V10CredentialExchange(**event.payload)
        cred_model = credential_record_to_model_v1(cred_exchange)
    # v2
    elif event.acapy_topic == "issue_credential_v2_0":
        cred_exchange = V20CredExRecord(**event.payload)
        cred_model = credential_record_to_model_v2(cred_exchange)
    else:
        raise Exception(f"Unsupported credential acapy topic: `{event.acapy_topic}`.")

    return cred_model


def to_proof_model(event: AcaPyWebhookEvent) -> PresentationExchange:
    # v1
    if event.acapy_topic == "present_proof":
        presentation_exchange = V10PresentationExchange(**event.payload)
        presentation_exchange = presentation_record_to_model(presentation_exchange)
    # v2
    elif event.acapy_topic == "present_proof_v2_0":
        presentation_exchange = V20PresExRecord(**event.payload)
        presentation_exchange = presentation_record_to_model(presentation_exchange)
    else:
        raise Exception(f"Unsupported proof acapy topic: `{event.acapy_topic}`.")

    return presentation_exchange


# Define the type of the transformer functions above
ModelTransformerFunction = Callable[[AcaPyWebhookEvent], WebhookEventPayloadType]

# Define a mapping from topics to their transformer functions
topic_to_transformer: Dict[CloudApiTopics, ModelTransformerFunction] = {
    "proofs": to_proof_model,
    "credentials": to_credential_model,
    "connections": to_connections_model,
    "basic-messages": to_basic_message_model,
    "endorsements": to_endorsement_model,
    "oob": to_oob_model,
    "revocation": to_revocation_model,
    "issuer_cred_rev": to_issuer_cred_rev_model,
    "problem_report": to_problem_report_model,
}


def transform_webhook_payload(
    acapy_event: AcaPyWebhookEvent,
) -> Optional[WebhookEventPayloadType]:
    transformer: Optional[ModelTransformerFunction] = topic_to_transformer.get(
        acapy_event.topic
    )

    if transformer:
        return transformer(acapy_event)


def acapy_to_cloudapi_event(
    acapy_event: AcaPyWebhookEvent,
) -> Optional[CloudApiWebhookEvent]:
    transformed_payload: Optional[WebhookEventPayloadType] = transform_webhook_payload(
        acapy_event
    )

    if transformed_payload:
        return CloudApiWebhookEvent(
            topic=acapy_event.topic,
            wallet_id=acapy_event.wallet_id,
            origin=acapy_event.origin,
            payload=transformed_payload,
        )
