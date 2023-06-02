from aries_cloudcontroller import (
    ConnRecord,
    V10CredentialExchange,
    V10PresentationExchange,
    V20CredExRecord,
    V20PresExRecord,
)

from shared import (
    Connection,
    CredentialExchange,
    Endorsement,
    PresentationExchange,
    RedisItem,
    conn_record_to_connection,
    credential_record_to_model_v1,
    credential_record_to_model_v2,
    presentation_record_to_model,
)


def to_endorsement_model(item: RedisItem) -> Endorsement:
    if item["payload"]["state"]:
        item["payload"]["state"] = item["payload"]["state"].replace("_", "-")
    return Endorsement(**item["payload"])


def to_connections_model(item: RedisItem) -> Connection:
    conn_record = ConnRecord(**item["payload"])
    conn_record = conn_record_to_connection(connection_record=conn_record)

    return conn_record


def to_proof_hook_model(item: RedisItem) -> PresentationExchange:
    # v1
    if item["acapy_topic"] == "present_proof":
        presentation_exchange = V10PresentationExchange(**item["payload"])
        presentation_exchange = presentation_record_to_model(presentation_exchange)
    # v2
    elif item["acapy_topic"] == "present_proof_v2_0":
        presentation_exchange = V20PresExRecord(**item["payload"])
        presentation_exchange = presentation_record_to_model(presentation_exchange)
    else:
        topic = item["acapy_topic"]
        raise Exception(f"Unsupported proof acapy topic: {topic}")

    return presentation_exchange


def to_credential_hook_model(item: RedisItem) -> CredentialExchange:
    # v1
    if item["acapy_topic"] == "issue_credential":
        cred_exchange = V10CredentialExchange(**item["payload"])
        cred_model = credential_record_to_model_v1(cred_exchange)
    # v2
    elif item["acapy_topic"] == "issue_credential_v2_0":
        cred_exchange = V20CredExRecord(**item["payload"])
        cred_model = credential_record_to_model_v2(cred_exchange)
    else:
        topic = item["acapy_topic"]
        raise Exception(f"Unsupported issue credential acapy topic: {topic}")

    return cred_model
