import json
import base64
from enum import Enum
from typing import Union
from typing import List, Literal
from aries_cloudcontroller import AcaPyClient

from httpx import AsyncClient, get, HTTPError

from app.constants import WEBHOOKS_URL
from app.constants import GOVERNANCE_AGENT_API_KEY
from app.constants import GOVERNANCE_AGENT_API_KEY as OOB_ADMIN_API_KEY
from app.constants import MEMBER_AGENT_API_KEY as MEMBER_ADMIN_API_KEY


topics = Literal[
    "connections",
    "issue_credential",
    "forward",
    "ping",
    "basicmessages",
    "issuer_cred_rev",
    "issue_credential_v2_0",
    "issue_credential_v2_0_indy",
    "issue_credential_v2_0_dif",
    "present_proof",
    "present_proof_v2_0",
    "revocation_registry",
]


class AdminAgentType(Enum):
    governance = "governance"
    oob = "oob"
    tenant = "tenant"


class AdminKeyMappings(Enum):
    governance = GOVERNANCE_AGENT_API_KEY
    oob = OOB_ADMIN_API_KEY
    tenant = MEMBER_ADMIN_API_KEY


def get_wallet_id_from_b64encoded_jwt(jwt: str) -> str:
    # Add padding if required
    # b64 needs lengths divisible by 4
    if len(jwt) % 4 != 0:
        n_missing = 4 - (len(jwt) % 4)
        jwt = jwt + (n_missing * "=")

    wallet = json.loads(base64.b64decode(jwt))
    return wallet["wallet_id"]


def get_wallet_id_from_client(client: AcaPyClient) -> str:
    if not is_tenant(client=client):
        return "admin"

    # eg tenenat_jwt: "eyJ3YWxsZXRfaWQiOiIwMzg4OTc0MC1iNDg4LTRmZjEtYWI4Ni0yOTM0NzQwZjNjNWMifQ"
    jwt = client.client.headers["authorization"].split(" ")[1].split(".")[1]

    return get_wallet_id_from_b64encoded_jwt(jwt)


def get_hooks_per_topic_per_wallet(client: AcaPyClient, topic: topics) -> List:
    if not is_tenant(client=client):
        wallet_id = "admin"
    else:
        wallet_id = get_wallet_id_from_client(client)
    try:
        hooks = (get(f"{WEBHOOKS_URL}/{topic}/{wallet_id}")).json()
        return hooks if hooks else []
    except HTTPError as e:
        raise e from e


def get_hooks_per_wallet(
    client: AcaPyClient,
) -> List:
    """
    Gets all webhooks for all wallets by topic (default="connections")
    """
    if not is_tenant(client=client):
        wallet_id = "admin"
    else:
        wallet_id = get_wallet_id_from_client(client)
    try:
        hooks = (get(f"{WEBHOOKS_URL}/{wallet_id}")).json()
        # Only return the first 100 hooks to prevent OpenAPI interface from crashing
        return hooks if hooks else []
    except HTTPError as e:
        raise e from e


def is_tenant(client: AcaPyClient):
    return "authorization" in client.client.headers
