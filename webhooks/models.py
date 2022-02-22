from typing_extensions import Literal
from aries_cloudcontroller import (
    ConnRecord,
    V10PresentationExchange,
    V20PresExRecord,
    V10CredentialExchange,
    V20CredExRecord,
)

from shared_models import (
    ConnectionsHook,
    credential_record_to_model_v1,
    PresentationExchange,
    CredentialExchange,
    HookBase,
    presentation_record_to_model,
    conn_record_to_connection,
    credential_record_to_model_v2,
)


def to_connections_model(item: dict) -> ConnectionsHook:
    conn_record = ConnRecord(**item)
    conn_record = conn_record_to_connection(connection_record=conn_record)

    merged_dicts = {**item, **conn_record.dict()}
    return ConnectionsHook(**merged_dicts)


class BasicMessagesHook(HookBase):
    connection_id: str
    content: str
    message_id: str
    sent_time: str
    state: Literal["received"]


class ProofsHook(HookBase, PresentationExchange):
    pass


def to_proof_hook_model(item: dict) -> ProofsHook:
    # v1
    if "presentation_exchange_id" in item:
        presentation_exchange = V10PresentationExchange(**item)
        presentation_exchange = presentation_record_to_model(presentation_exchange)
    # v2
    elif "pres_ex_id" in item:
        presentation_exchange = V20PresExRecord(**item)
        presentation_exchange = presentation_record_to_model(presentation_exchange)
    merged_dicts = {**item, **presentation_exchange.dict()}
    return ProofsHook(**merged_dicts)


class CredentialsHooks(HookBase, CredentialExchange):
    pass


def to_credentential_hook_model(item: dict) -> CredentialsHooks:
    # v1
    if "credential_exchange_id" in item:
        cred_exchange = V10CredentialExchange(**item)
        cred_model = credential_record_to_model_v1(cred_exchange)
    # v2
    elif "cred_ex_id" in item:
        cred_exchange = V20CredExRecord(**item)
        cred_model = credential_record_to_model_v2(cred_exchange)
    merged_dicts = {**item, **cred_model.dict()}
    return CredentialsHooks(**merged_dicts)
