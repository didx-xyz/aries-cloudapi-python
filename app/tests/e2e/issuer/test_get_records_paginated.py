import pytest
from fastapi import HTTPException

from app.tests.util.connections import FaberAliceConnect
from shared import RichAsyncClient

CREDENTIALS_BASE_PATH = "/v1/issuer/credentials"


@pytest.mark.anyio
async def test_get_credential_exchange_records_paginated(
    faber_client: RichAsyncClient,
    credential_definition_id: str,
    faber_and_alice_connection: FaberAliceConnect,
):
    num_credentials_to_test = 5
    test_attributes = {"speed": "20", "name": "Alice", "age": "44"}

    faber_cred_ex_ids = []
    # Create multiple credential exchanges
    for _ in range(num_credentials_to_test):
        credential_v2 = {
            "protocol_version": "v2",
            "connection_id": faber_and_alice_connection.faber_connection_id,
            "indy_credential_detail": {
                "credential_definition_id": credential_definition_id,
                "attributes": test_attributes,
            },
            "save_exchange_record": True,
        }

        response = await faber_client.post(CREDENTIALS_BASE_PATH, json=credential_v2)

        credential_exchange_id = response.json()["credential_exchange_id"]
        faber_cred_ex_ids.append(credential_exchange_id)

    # Test different limits
    for limit in range(1, num_credentials_to_test + 2):
        response = await faber_client.get(
            CREDENTIALS_BASE_PATH,
            params={
                "state": "offer-sent",
                "limit": limit,
            },
        )
        credentials = response.json()
        assert len(credentials) == min(limit, num_credentials_to_test)

    # Test offset greater than number of records
    response = await faber_client.get(
        CREDENTIALS_BASE_PATH,
        params={
            "state": "offer-sent",
            "limit": 1,
            "offset": num_credentials_to_test,
        },
    )
    credentials = response.json()
    assert len(credentials) == 0

    # Test fetching unique records with pagination
    prev_credentials = []
    for offset in range(num_credentials_to_test):
        response = await faber_client.get(
            CREDENTIALS_BASE_PATH,
            params={
                "state": "offer-sent",
                "limit": 1,
                "offset": offset,
            },
        )

        credentials = response.json()
        assert len(credentials) == 1

        record = credentials[0]
        assert record not in prev_credentials
        prev_credentials.append(record)

    # Test invalid limit and offset values
    invalid_params = [
        {"limit": -1},  # must be positive
        {"offset": -1},  # must be positive
        {"limit": 0},  # must be greater than 0
        {"limit": 10001},  # must be less than or equal to max in ACA-Py: 10'000
    ]

    for params in invalid_params:
        with pytest.raises(HTTPException) as exc:
            await faber_client.get(CREDENTIALS_BASE_PATH, params=params)
        assert exc.value.status_code == 422

    # Clean up created credentials
    for cred_ex_id in faber_cred_ex_ids:
        await faber_client.delete(f"{CREDENTIALS_BASE_PATH}/{cred_ex_id}")
