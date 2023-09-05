from dataclasses import dataclass
from random import random

import pytest

from app.routes.wallet import router
from app.services.trust_registry import (
    Actor,
    actor_by_did,
    register_actor,
    register_schema,
    registry_has_schema,
    remove_actor_by_id,
)
from shared import RichAsyncClient

WALLET_BASE_PATH = router.prefix


async def register_issuer(issuer_client: RichAsyncClient, schema_id: str):
    pub_did_res = await issuer_client.get(f"{WALLET_BASE_PATH}/public")
    did = pub_did_res.json()["did"]

    if not await registry_has_schema(schema_id=schema_id):
        await register_schema(schema_id)

    if not await actor_by_did(f"did:sov:{did}"):
        rand = random()
        await register_actor(
            Actor(
                id=f"test-actor-{rand}",
                name=f"Test Actor-{rand}",
                roles=["issuer", "verifier"],
                did=f"did:sov:{did}",
                didcomm_invitation=None,
            )
        )


@dataclass
class DidKey:
    did: str


@pytest.fixture(scope="function")
async def register_key_issuer_ed25519(faber_client: RichAsyncClient) -> DidKey:
    did_create_options = {"method": "key", "options": {"key_type": "ed25519"}}

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
            did=f"{did}",
            didcomm_invitation=None,
        )
    )

    yield did

    await remove_actor_by_id(test_id)


@pytest.fixture(scope="function")
async def register_key_issuer_bbs(faber_client: RichAsyncClient) -> DidKey:
    did_create_options = {"method": "key", "options": {"key_type": "bls12381g2"}}

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
            did=f"{did}",
            didcomm_invitation=None,
        )
    )

    yield did

    await remove_actor_by_id(test_id)
