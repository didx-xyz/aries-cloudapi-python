import logging
from typing import List, Literal, Optional

import httpx
from fastapi.exceptions import HTTPException
from typing_extensions import TypedDict
from app.constants import TRUST_REGISTRY_URL

logger = logging.getLogger(__name__)

Role = Literal["issuer", "verifier"]


class TrustRegistryException(Exception):
    """Class that represents a trust registry error"""

    pass


class Actor(TypedDict):
    id: str
    name: str
    roles: List[str]
    did: str
    didcomm_invitation: Optional[str]


class TrustRegistry(TypedDict):
    actors: List[Actor]
    schemas: List[str]


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
        raise TrustRegistryException(f"Did {did} not registered in the trust registry")

    actor_id = actor["id"]
    if not "issuer" in actor["roles"]:
        raise TrustRegistryException(
            f"Actor {actor_id} does not have required role 'issuer'"
        )

    has_schema = await registry_has_schema(schema_id)
    if not has_schema:
        raise TrustRegistryException(
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
        raise TrustRegistryException(f"Did {did} not registered in the trust registry")

    actor_id = actor["id"]
    if not "verifier" in actor["roles"]:
        raise TrustRegistryException(
            f"Actor {actor_id} does not have required role 'verifier'"
        )

    has_schema = await registry_has_schema(schema_id)
    if not has_schema:
        raise TrustRegistryException(
            f"Schema with id {schema_id} is not registered in trust registry"
        )


async def actor_has_role(actor_id: str, role: Role) -> bool:
    actor_res = httpx.get(TRUST_REGISTRY_URL + f"/registry/actors/{actor_id}")
    if actor_res.status_code != 200:
        raise HTTPException(404, detail="Actor does not exist")
    return bool(role in actor_res.json()["roles"])


async def actor_by_did(did: str) -> Optional[Actor]:
    actor_res = httpx.get(TRUST_REGISTRY_URL + f"/registry/actors/did/{did}")

    if actor_res.status_code == 404:
        return None
    if actor_res.status_code != 200:
        raise HTTPException(500, f"Error fetching actor by did: {actor_res.text}")

    return actor_res.json()


async def actors_with_role(role: Role) -> List[Actor]:
    actors = httpx.get(TRUST_REGISTRY_URL + "/registry/actors")
    if actors.status_code != 200:
        return []
    actors_with_role_list = [
        actor for actor in actors.json()["actors"] if role in actor["roles"]
    ]
    return actors_with_role_list


async def actor_has_schema(actor_id: str, schema_id: str) -> bool:
    actor_res = httpx.get(TRUST_REGISTRY_URL + f"/registry/actors/{actor_id}")
    if actor_res.status_code != 200:
        return False
    return bool(schema_id in actor_res.json()["schemas"])


async def registry_has_schema(schema_id: str) -> bool:
    schema_res = httpx.get(TRUST_REGISTRY_URL + "/registry/schemas")
    if schema_res.status_code != 200:
        return False
    return bool(schema_id in schema_res.json()["schemas"])


async def get_did_for_actor(actor_id: str) -> List[str]:
    actor_res = httpx.get(TRUST_REGISTRY_URL + f"/registry/actors/{actor_id}")
    if actor_res.status_code != 200:
        return None
    did = actor_res.json()["did"]
    didcomm_invitation = actor_res.json()["didcomm_invitation"]
    return [did, didcomm_invitation]


async def get_trust_registry() -> TrustRegistry:
    trust_registry_res = httpx.get(f"{TRUST_REGISTRY_URL}/registry")

    if trust_registry_res.status_code != 200:
        raise HTTPException(500, detail=trust_registry_res.content)

    return trust_registry_res.json()


async def register_schema(schema_id: str) -> None:
    schema_res = httpx.post(
        TRUST_REGISTRY_URL + "/registry/schemas", json={"schema_id": schema_id}
    )

    if schema_res.status_code != 200:
        raise Exception(f"Error registering schema {schema_id}: {schema_res.text}")


async def register_actor(actor: Actor) -> None:
    actor_res = httpx.post(TRUST_REGISTRY_URL + "/registry/actors", json=actor)

    if actor_res.status_code != 200:
        raise Exception(f"Error registering actor: {actor_res.text}")
