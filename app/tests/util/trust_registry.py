from random import random

from app.routes.wallet import router
from app.services.trust_registry import (
    Actor,
    actor_by_did,
    register_actor,
    register_schema,
    registry_has_schema,
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
