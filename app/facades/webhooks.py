import json
import base64
import os
from typing import List, Literal
from aries_cloudcontroller import AcaPyClient

import httpx


BROADCAST_URL = os.getenv("BROADCAST_URL", "http://yoma-webhooks-web:3010")
ADMIN_API_KEY = os.getenv("ACAPY_ADMIN_API_KEY", "adminApiKey")

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
    "revocation_registry",
]


def get_wallet_id_from_client(client: AcaPyClient) -> str:

    jwt = client.tenant_jwt
    if len(jwt) % 4 != 0:
        n_missing = len(jwt) % 4
        jwt_64 = jwt + n_missing * "="

    wallet = json.loads(base64.b64decode(jwt_64))
    return wallet["wallet_id"]


def get_hooks_per_topic_per_wallet(client: AcaPyClient, topic: topics) -> List:
    wallet_id = get_wallet_id_from_client(client)
    try:
        hooks = (httpx.get(f"{BROADCAST_URL}/{topic}/{wallet_id}")).json()
        return hooks if hooks else []
    except httpx.HTTPError as e:
        raise e from e


def get_hooks_per_topic_admin(client: AcaPyClient, topic: topics) -> List:
    """
    Gets all webhooks for all wallets by topic (default="connections")
    """
    try:
        assert client.client.headers["x-api-key"] == ADMIN_API_KEY
        hooks = (httpx.get(f"{BROADCAST_URL}/connections")).json()
        # Only return the first 100 hooks to prevent OpenAPI interface from crashing
        return hooks[:100] if hooks else []
    except httpx.HTTPError as e:
        raise e from e
