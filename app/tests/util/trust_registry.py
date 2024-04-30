from contextlib import asynccontextmanager
from random import random
from typing import AsyncGenerator

from app.models.trust_registry import Actor
from app.routes.wallet.dids import router as wallet_router
from app.services.trust_registry.actors import (
    fetch_actor_by_did,
    register_actor,
    remove_actor_by_id,
)
from app.services.trust_registry.schemas import register_schema
from app.services.trust_registry.util.schema import registry_has_schema
from shared import RichAsyncClient

WALLET_BASE_PATH = wallet_router.prefix


async def register_issuer(issuer_client: RichAsyncClient, schema_id: str):
    pub_did_res = await issuer_client.get(f"{WALLET_BASE_PATH}/public")
    did = pub_did_res.json()["did"]

    if not await registry_has_schema(schema_id=schema_id):
        await register_schema(schema_id)

    if not await fetch_actor_by_did(f"did:sov:{did}"):
        rand = random()
        await register_actor(
            Actor(
                id=f"test-actor-{rand}",
                name=f"Test Actor-{rand}",
                roles=["issuer"],
                did=f"did:sov:{did}",
                didcomm_invitation=None,
            )
        )


@asynccontextmanager
async def register_issuer_key(
    faber_client: RichAsyncClient, key_type: str
) -> AsyncGenerator[str, None]:
    did_create_options = {"method": "key", "options": {"key_type": key_type}}

    wallet_response = (
        await faber_client.post(WALLET_BASE_PATH, json=did_create_options)
    ).json()
    did = wallet_response["did"]

    rand = random()
    test_id = f"test-actor-{rand}"

    await register_actor(
        Actor(
            id=test_id,
            name=f"Test Actor-{rand}",
            roles=["issuer"],
            did=did,
            didcomm_invitation=None,
        )
    )

    try:
        yield did
    finally:
        await remove_actor_by_id(test_id)
