import app.utils as utils
from app.utils import ed25519_verkey_to_did_key

ID_CONSTANT = "abcde:test:0.0.1"


def test_construct_zkp():
    given = [[{"name": "name", "p_type": ">=", "p_value": "21"}], ID_CONSTANT]
    expected = [
        {
            "name": "name",
            "p_type": ">=",
            "p_value": "21",
            "restrictions": [{"schema_id": ID_CONSTANT}],
        }
    ]

    result = utils.construct_zkp(*given)

    assert result == expected


def test_construct_zkp_empty():
    given = [{}]
    expect = []

    result = utils.construct_zkp(given, "1234")

    assert result == expect


def test_construct_indy_proof_request():
    given = [
        "abcde",
        ID_CONSTANT,
        [{"name": "name"}, {"name": "age"}],
        [{"name": "name", "p_type": ">=", "p_value": "21"}],
    ]

    expected = {
        "name": "abcde",
        "requested_attributes": {
            "0_age_uuid": {"name": "age"},
            "0_name_uuid": {"name": "name"},
        },
        "requested_predicates": {
            "0_name_GE_uuid": {"name": "name", "p_type": ">=", "p_value": "21"}
        },
        "version": "0.0.1",
    }

    result = utils.construct_indy_proof_request(*given)

    assert result == expected


def test_ed25519_verkey_to_did_key():
    verkey = "8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"
    did_key = "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"

    assert ed25519_verkey_to_did_key(verkey) == did_key
