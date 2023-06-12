import base58


def ed25519_verkey_to_did_key(key: str) -> str:
    """Convert a naked ed25519 verkey to W3C did:key format."""
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
