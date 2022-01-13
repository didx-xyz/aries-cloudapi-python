from app.util.did import ed25519_verkey_to_did_key, qualified_did_sov


def test_ed25519_verkey_to_did_key():
    verkey = "8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"
    did_key = "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"

    assert ed25519_verkey_to_did_key(verkey) == did_key


def test_qualified_did_sov(did: str):
    unqualified_did = "8HH5gYEeNc3z7PYX"
    qualified_did = f"did:sov:{unqualified_did}"

    assert qualified_did_sov(unqualified_did) == qualified_did
    assert qualified_did_sov(qualified_did) == qualified_did
