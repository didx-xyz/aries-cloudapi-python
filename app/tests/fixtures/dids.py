from typing import AsyncGenerator

import pytest

from app.tests.util.trust_registry import DidKey, register_issuer_key
from shared import RichAsyncClient


@pytest.fixture(scope="function")
async def register_issuer_key_ed25519(
    faber_client: RichAsyncClient,
) -> AsyncGenerator[DidKey, None]:
    async with register_issuer_key(faber_client, "ed25519") as did:
        yield did


@pytest.fixture(scope="function")
async def register_issuer_key_bbs(
    faber_client: RichAsyncClient,
) -> AsyncGenerator[DidKey, None]:
    async with register_issuer_key(faber_client, "bls12381g2") as did:
        yield did
