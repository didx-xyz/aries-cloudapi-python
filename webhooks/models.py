import json

from typing_extensions import Literal
from pydantic import ValidationError

from shared_models import (
    Connection,
    PresentationExchange,
    CredentialExchange,
    HookBase,
)


class ConnectionsHook(HookBase, Connection):
    pass


def to_connections_model(item: dict) -> ConnectionsHook:
    item["state"] = item.pop("rfc23_state")
    try:
        item = ConnectionsHook(**item)
    except ValidationError:
        pass
    return item


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
        item["protocol_version"] = "v1"
        item["proof_id"] = "v1-" + item["presentation_exchange_id"]
        try:
            item["state"] = item["state"].replace("_", "-")
        except KeyError:
            pass
    # v2
    elif "pres_ex_id" in item:
        item["proof_id"] = "v2-" + item["pres_ex_id"]
        item["protocol_version"] = "v2"
        try:
            item["presentation_request"] = item["by_format"]["pres_request"]["indy"]
        except KeyError:
            pass
        try:
            item["presentation"] = item["by_format"]["pres"]["indy"]
        except KeyError:
            pass
    # error msg instead - request abandoned
    if "state" not in item:
        item["state"] = "abandoned"
    try:
        item["verified"] = json.loads(item["verified"])
    except KeyError:
        pass
    return ProofsHook(**item)


class CredentialsHooks(HookBase, CredentialExchange):
    pass


def to_credentential_hook_model(item: dict) -> CredentialsHooks:
    if "credential_exchange_id" in item:
        item["protocol_version"] = "v1"
        item["credential_id"] = "v1-" + item["credential_exchange_id"]
        item["credential_proposal"] = item["credential_proposal_dict"]
        try:
            item["state"] = item["state"].replace("_", "-")
        except KeyError:
            pass
    elif "cred_ex_id" in item:
        item["protocol_version"] = "v2"
        item["cred_ex_id"] = "v2-" + item["cred_ex_id"]
        item["credential_id"] = item.pop("cred_ex_id")
        try:
            item["credential_definition_id"] = item["by_format"]["cred_offer"]["indy"][
                "cred_def_id"
            ]
        except KeyError:
            pass
        try:
            item["credential_offer"] = item["by_format"]["cred_offer"]
        except KeyError:
            pass
        try:
            item["credential_proposal"] = item["cred_proposal"]
        except KeyError:
            pass
    try:
        item["attributes"] = item["credential_proposal"]["credential_proposal"][
            "attributes"
        ]
    except (KeyError, TypeError):
        pass
    return CredentialsHooks(**item)
