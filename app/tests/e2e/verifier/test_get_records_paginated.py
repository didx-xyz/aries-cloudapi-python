import asyncio

import pytest
from fastapi import HTTPException

from app.routes.verifier import router
from app.tests.services.verifier.utils import sample_indy_proof_request
from app.tests.util.connections import AcmeAliceConnect
from app.tests.util.regression_testing import TestMode
from app.tests.util.verifier import send_proof_request
from shared import RichAsyncClient

VERIFIER_BASE_PATH = router.prefix


@pytest.mark.anyio
@pytest.mark.skipif(
    TestMode.regression_run in TestMode.fixture_params,
    reason="Temporarily skip; existing tests on dev don't clean up old records yet",
)
async def test_get_presentation_exchange_records_paginated(
    acme_client: RichAsyncClient,
    credential_definition_id: str,
    acme_and_alice_connection: AcmeAliceConnect,
):
    num_presentation_requests_to_test = 5

    acme_proof_ids = []
    acme_connection_id = acme_and_alice_connection.acme_connection_id

    # Create multiple presentation requests
    for _ in range(num_presentation_requests_to_test):
        request_body = {
            "save_exchange_record": True,
            "connection_id": acme_connection_id,
            "protocol_version": "v2",
            "indy_proof_request": sample_indy_proof_request(
                restrictions=[{"cred_def_id": credential_definition_id}]
            ).to_dict(),
        }
        response = await send_proof_request(acme_client, request_body)
        acme_proof_ids.append(response["proof_id"])

    # Test different limits
    for limit in range(1, num_presentation_requests_to_test + 2):
        num_tries = 0
        retry = True
        while retry and num_tries < 5:  # Handle case where record doesn't exist yet
            response = await acme_client.get(
                f"{VERIFIER_BASE_PATH}/proofs",
                params={
                    "state": "request-sent",
                    "limit": limit,
                },
            )
            proofs = response.json()
            if len(proofs) != min(limit, num_presentation_requests_to_test):
                num_tries += 1
                await asyncio.sleep(0.2)
            else:
                retry = False
        assert not retry, f"Expected {limit} records, got {len(proofs)}: {proofs}"

    # Test offset greater than number of records
    response = await acme_client.get(
        f"{VERIFIER_BASE_PATH}/proofs",
        params={
            "state": "request-sent",
            "limit": 1,
            "offset": num_presentation_requests_to_test,
        },
    )
    proofs = response.json()
    assert len(proofs) == 0

    # Test fetching unique records with pagination
    # TODO: Skipping for now; we require ACA-Py / Askar record ordering to guarantee unique records across pages
    # prev_proofs = []
    # for offset in range(num_presentation_requests_to_test):
    #     response = await acme_client.get(
    #         f"{VERIFIER_BASE_PATH}/proofs",
    #         params={
    #             "state": "request-sent",
    #             "limit": 1,
    #             "offset": offset,
    #         },
    #     )

    #     proofs = response.json()
    #     assert len(proofs) == 1

    #     record = proofs[0]
    #     assert record not in prev_proofs
    #     prev_proofs.append(record)

    # Test invalid limit and offset values
    invalid_params = [
        {"limit": -1},  # must be positive
        {"offset": -1},  # must be positive
        {"limit": 0},  # must be greater than 0
        {"limit": 10001},  # must be less than or equal to max in ACA-Py: 10'000
    ]

    for params in invalid_params:
        with pytest.raises(HTTPException) as exc:
            await acme_client.get(f"{VERIFIER_BASE_PATH}/proofs", params=params)
        assert exc.value.status_code == 422

    # Clean up created presentation requests
    for proof_id in acme_proof_ids:
        await acme_client.delete(f"{VERIFIER_BASE_PATH}/proofs/{proof_id}")
