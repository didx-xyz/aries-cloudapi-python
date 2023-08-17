import re

import base58


def ed25519_verkey_to_did_key(key: str) -> str:
    """Convert a naked ed25519 verkey to W3C did:key format."""

    # Length validation
    if len(key) not in (43, 44):
        raise ValueError(
            "Invalid key length. ed25519 keys should be 43 or 44 characters long when base58 encoded."
        )

    # Character set validation
    if not re.match(
        "^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+$", key
    ):
        raise ValueError(
            "Invalid key. ed25519 keys should only contain base58 characters."
        )

    key_bytes = base58.b58decode(key)
    prefixed_key_bytes = b"".join([b"\xed\x01", key_bytes])
    fingerprint = base58.b58encode(prefixed_key_bytes).decode("ascii")
    did_key = f"did:key:z{fingerprint}"
    return did_key


def qualified_did_sov(did: str) -> str:
    if not did.startswith("did:sov:"):
        return f"did:sov:{did}"

    return did


def did_from_credential_definition_id(credential_definition_id: str) -> str:
    parts = credential_definition_id.split(":")

    return parts[0]
