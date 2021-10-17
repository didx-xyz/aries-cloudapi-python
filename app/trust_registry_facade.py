import logging
import os
from typing import Literal, List
from fastapi.exceptions import HTTPException

import requests

TRUST_REGISTRY_URL = os.getenv("TRUST_REGISTRY_URL", "http://localhost:8001/")

logger = logging.getLogger(__name__)

Role = Literal["issuer", "verifier"]


async def assert_valid_issuer(did: str, schema_id: str):
    """Assert that an actor with the specified did is registered as issuer.

    This method asserts that there is an actor registered in the trust registry
    with the specified did. It verifies whether this actor has the `issuer` role
    and will also make sure the specified schema_id is regsitred as a valid schema.
    Raises an exception if one of the assertions fail.

    NOTE: the dids in the registry are registered as fully qualified dids. This means
    when passing a did to this method it must also be fully qualified (e.g. `did:sov:xxxx`)

    Args:
        did (str): the did of the issuer in fully qualified format.
        schema_id (str): the schema_id of the credential being issued

    Raises:
        Exception: When the did is not registered, the actor doesn't have the issuer role
            or the schema is not registered in the registry.
    """
    actor = await actor_by_did(did)

    if not actor:
        raise Exception(f"Did {did} not registered in the trust registry")

    actor_id = actor["id"]
    if not "issuer" in actor["roles"]:
        raise Exception(f"Actor {actor_id} does not have required role 'issuer'")

    has_schema = await registry_has_schema(schema_id)
    if not has_schema:
        raise Exception(
            f"Schema with id {schema_id} is not registered in trust registry"
        )


async def assert_valid_verifier(did: str, schema_id: str):
    """Assert that an actor with the specified did is registered as verifier.

    This method asserts that there is an actor registered in the trust registry
    with the specified did. It verifies whether this actor has the `verifier` role
    and will also make sure the specified schema_id is regsitred as a valid schema.
    Raises an exception if one of the assertions fail.

    NOTE: the dids in the registry are registered as fully qualified dids. This means
    when passing a did to this method it must also be fully qualified (e.g. `did:sov:xxxx`)

    Args:
        did (str): the did of the verifier in fully qualified format.
        schema_id (str): the schema_id of the credential being issued

    Raises:
        Exception: When the did is not registered, the actor doesn't have the verifier role
            or the schema is not registered in the registry.
    """
    actor = await actor_by_did(did)

    if not actor:
        raise Exception(f"Did {did} not registered in the trust registry")

    actor_id = actor["id"]
    if not "verifier" in actor["roles"]:
        raise Exception(f"Actor {actor_id} does not have required role 'verifier'")

    has_schema = await registry_has_schema(schema_id)
    if not has_schema:
        raise Exception(
            f"Schema with id {schema_id} is not registered in trust registry"
        )


async def actor_has_role(actor_id: str, role: Role) -> bool:
    actor_res = requests.get(TRUST_REGISTRY_URL + f"/registry/actors/{actor_id}")
    if actor_res.status_code != 200:
        raise HTTPException(404, detail="Actor does not exist")
    return bool(role in actor_res.json()["roles"])


async def actor_by_did(did: str):
    actor_res = requests.get(TRUST_REGISTRY_URL + f"registry/actors/did/{did}")

    if actor_res.status_code != 200:
        return None

    return actor_res.json()


async def actors_with_role(role: Role) -> list:
    actors = requests.get(TRUST_REGISTRY_URL + "/registry/actors")
    if actors.status_code != 200:
        return []
    actors_with_role_list = [
        actor for actor in actors.json()["actors"] if role in actor["roles"]
    ]
    return actors_with_role_list


async def actor_has_schema(actor_id: str, schema_id: str) -> bool:
    actor_res = requests.get(TRUST_REGISTRY_URL + f"/registry/actors/{actor_id}")
    if actor_res.status_code != 200:
        return False
    return bool(schema_id in actor_res.json()["schemas"])


async def registry_has_schema(schema_id: str) -> bool:
    schema_res = requests.get(TRUST_REGISTRY_URL + "/registry/schemas")
    if schema_res.status_code != 200:
        return False
    return bool(schema_id in schema_res.json()["schemas"])


async def get_did_for_actor(actor_id: str) -> List[str]:
    actor_res = requests.get(TRUST_REGISTRY_URL + f"/registry/actors/{actor_id}")
    if actor_res.status_code != 200:
        return None
    did = actor_res.json()["did"]
    didcomm_invitation = actor_res.json()["didcomm_invitation"]
    return [did, didcomm_invitation]
