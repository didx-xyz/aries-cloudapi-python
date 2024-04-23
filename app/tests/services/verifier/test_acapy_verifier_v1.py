import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    ApiException,
    DIFProofRequest,
    IndyCredInfo,
    IndyCredPrecis,
    IndyPresSpec,
    PresentationDefinition,
    V10PresentationExchangeList,
)
from mockito import when

from app.exceptions.cloudapi_exception import CloudApiException
from app.models.verifier import ProofRequestType
from app.routes.verifier import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
)
from app.services.verifier.acapy_verifier_v1 import VerifierV1
from app.tests.services.verifier.utils import (
    indy_proof_request,
    v10_presentation_exchange_records,
)
from app.tests.util.mock import to_async
from shared.models.presentation_exchange import PresentationExchange
from shared.models.presentation_exchange import (
    presentation_record_to_model as record_to_model,
)
from shared.models.protocol import PresentProofProtocolVersion


@pytest.mark.anyio
async def test_create_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).create_proof_request(...).thenReturn(
        to_async(v10_presentation_exchange_records[0])
    )

    created_proof_request = await VerifierV1.create_proof_request(
        controller=mock_agent_controller,
        create_proof_request=CreateProofRequest(
            indy_proof_request=indy_proof_request,
            protocol_version=PresentProofProtocolVersion.V1,
        ),
    )

    assert isinstance(created_proof_request, PresentationExchange)


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [400, 500])
@pytest.mark.parametrize("error_detail", ["Error msg", "is dynamic"])
async def test_create_proof_request_exception(
    mock_agent_controller: AcaPyClient, status_code: int, error_detail: str
):
    when(mock_agent_controller.present_proof_v1_0).create_proof_request(...).thenRaise(
        ApiException(reason=error_detail, status=status_code)
    )

    with pytest.raises(
        CloudApiException,
        match=f"Failed to create presentation request: {error_detail}.",
    ) as exc:
        await VerifierV1.create_proof_request(
            controller=mock_agent_controller,
            create_proof_request=CreateProofRequest(
                indy_proof_request=indy_proof_request,
                protocol_version=PresentProofProtocolVersion.V1,
            ),
        )

    assert exc.value.status_code == status_code


@pytest.mark.anyio
async def test_send_proof_request(mock_agent_controller: AcaPyClient):
    # Mock different functions on AcaPy client present proof api
    # proof interface decides upon params which methods it calls on the client
    # so let's mock those methods out
    when(mock_agent_controller.present_proof_v1_0).send_presentation(...).thenReturn(
        v10_presentation_exchange_records[0]
    )  # todo: all of the mocks with to_async removed are unnecessary and have no effect
    when(mock_agent_controller.present_proof_v1_0).send_proposal(...).thenReturn(
        v10_presentation_exchange_records[0]
    )
    when(mock_agent_controller.present_proof_v1_0).send_request(...).thenReturn(
        v10_presentation_exchange_records[0]
    )
    when(mock_agent_controller.present_proof_v1_0).send_request_free(...).thenReturn(
        to_async(v10_presentation_exchange_records[0])
    )

    created_proof_send_proposal = await VerifierV1.send_proof_request(
        controller=mock_agent_controller,
        send_proof_request=SendProofRequest(
            connection_id="abcde",
            indy_proof_request=indy_proof_request,
            protocol_version=PresentProofProtocolVersion.V1,
        ),
    )

    assert isinstance(created_proof_send_proposal, PresentationExchange)


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [400, 500])
@pytest.mark.parametrize("error_detail", ["Error msg", "is dynamic"])
async def test_send_proof_request_exception(
    mock_agent_controller: AcaPyClient, status_code: int, error_detail: str
):
    when(mock_agent_controller.present_proof_v1_0).send_request_free(...).thenRaise(
        ApiException(reason=error_detail, status=status_code)
    )

    with pytest.raises(
        CloudApiException,
        match=f"Failed to send presentation request: {error_detail}.",
    ) as exc:
        await VerifierV1.send_proof_request(
            controller=mock_agent_controller,
            send_proof_request=SendProofRequest(
                indy_proof_request=indy_proof_request,
                protocol_version=PresentProofProtocolVersion.V1,
                connection_id="abc",
            ),
        )

    assert exc.value.status_code == status_code


@pytest.mark.anyio
async def test_accept_proof_request(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).send_presentation(...).thenReturn(
        to_async(v10_presentation_exchange_records[0])
    )

    accepted_proof_request = await VerifierV1.accept_proof_request(
        mock_agent_controller,
        accept_proof_request=AcceptProofRequest(
            proof_id="v1-123",
            indy_presentation_spec=IndyPresSpec(
                requested_attributes={},
                requested_predicates={},
                self_attested_attributes={},
            ),
        ),
    )

    assert isinstance(accepted_proof_request, PresentationExchange)


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [400, 500])
@pytest.mark.parametrize("error_detail", ["Error msg", "is dynamic"])
async def test_accept_proof_request_exception(
    mock_agent_controller: AcaPyClient, status_code: int, error_detail: str
):
    when(mock_agent_controller.present_proof_v1_0).send_presentation(...).thenRaise(
        ApiException(reason=error_detail, status=status_code)
    )

    with pytest.raises(
        CloudApiException,
        match=f"Failed to send proof presentation: {error_detail}.",
    ) as exc:
        await VerifierV1.accept_proof_request(
            controller=mock_agent_controller,
            accept_proof_request=AcceptProofRequest(
                proof_id="v1-123",
                indy_presentation_spec=IndyPresSpec(
                    requested_attributes={},
                    requested_predicates={},
                    self_attested_attributes={},
                ),
            ),
        )

    assert exc.value.status_code == status_code


@pytest.mark.anyio
async def test_reject_proof_reject(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).delete_record(...).thenReturn(
        to_async({})
    )
    when(mock_agent_controller.present_proof_v1_0).report_problem(...).thenReturn(
        to_async({})
    )
    when(mock_agent_controller.present_proof_v1_0).get_record(...).thenReturn(
        v10_presentation_exchange_records[0]
    )

    deleted_proof_request = await VerifierV1.reject_proof_request(
        controller=mock_agent_controller,
        reject_proof_request=RejectProofRequest(
            proof_id="v1-abc", problem_report="some message", delete_proof_record=True
        ),
    )

    assert deleted_proof_request is None


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [400, 500])
@pytest.mark.parametrize("error_detail", ["Error msg", "is dynamic"])
async def test_reject_proof_reject_exception_report(
    mock_agent_controller: AcaPyClient, status_code: int, error_detail: str
):
    when(mock_agent_controller.present_proof_v1_0).report_problem(...).thenRaise(
        ApiException(reason=error_detail, status=status_code)
    )

    with pytest.raises(
        CloudApiException,
        match=f"Failed to send problem report: {error_detail}.",
    ) as exc:
        await VerifierV1.reject_proof_request(
            controller=mock_agent_controller,
            reject_proof_request=RejectProofRequest(
                proof_id="v1-abc", problem_report="bad"
            ),
        )

    assert exc.value.status_code == status_code


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [400, 500])
@pytest.mark.parametrize("error_detail", ["Error msg", "is dynamic"])
async def test_reject_proof_reject_exception_delete(
    mock_agent_controller: AcaPyClient, status_code: int, error_detail: str
):
    when(mock_agent_controller.present_proof_v1_0).report_problem(...).thenReturn(
        to_async({})
    )
    when(mock_agent_controller.present_proof_v1_0).delete_record(...).thenRaise(
        ApiException(reason=error_detail, status=status_code)
    )

    with pytest.raises(
        CloudApiException,
        match=f"Failed to delete record: {error_detail}.",
    ) as exc:
        await VerifierV1.reject_proof_request(
            controller=mock_agent_controller,
            reject_proof_request=RejectProofRequest(
                proof_id="v1-abc", problem_report="bad", delete_proof_record=True
            ),
        )

    assert exc.value.status_code == status_code


@pytest.mark.anyio
async def test_get_proof_records(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).get_records(...).thenReturn(
        to_async(V10PresentationExchangeList(results=v10_presentation_exchange_records))
    )

    proof_records = await VerifierV1.get_proof_records(
        controller=mock_agent_controller,
    )

    expected_result = [
        record_to_model(rec) for rec in v10_presentation_exchange_records
    ]
    assert proof_records == expected_result


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [400, 500])
@pytest.mark.parametrize("error_detail", ["Error msg", "is dynamic"])
async def test_get_proof_records_exception(
    mock_agent_controller: AcaPyClient, status_code: int, error_detail: str
):
    when(mock_agent_controller.present_proof_v1_0).get_records(...).thenRaise(
        ApiException(reason=error_detail, status=status_code)
    )

    with pytest.raises(
        CloudApiException,
        match=f"Failed to get proof records: {error_detail}.",
    ) as exc:
        await VerifierV1.get_proof_records(
            controller=mock_agent_controller,
        )

    assert exc.value.status_code == status_code


@pytest.mark.anyio
async def test_get_proof_record(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).get_record(...).thenReturn(
        to_async(v10_presentation_exchange_records[0])
    )

    proof_record = await VerifierV1.get_proof_record(
        controller=mock_agent_controller, proof_id="v1-abc"
    )

    expected_result = record_to_model(v10_presentation_exchange_records[0])
    assert proof_record == expected_result


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [400, 500])
@pytest.mark.parametrize("error_detail", ["Error msg", "is dynamic"])
async def test_get_proof_record_exception(
    mock_agent_controller: AcaPyClient, status_code: int, error_detail: str
):
    when(mock_agent_controller.present_proof_v1_0).get_record(...).thenRaise(
        ApiException(reason=error_detail, status=status_code)
    )
    proof_id = "v1-abc"
    with pytest.raises(
        CloudApiException,
        match=f"Failed to get proof record with proof id `{proof_id}`: {error_detail}.",
    ) as exc:
        await VerifierV1.get_proof_record(
            controller=mock_agent_controller, proof_id=proof_id
        )

    assert exc.value.status_code == status_code


@pytest.mark.anyio
async def test_delete_proof(mock_agent_controller: AcaPyClient):
    when(mock_agent_controller.present_proof_v1_0).delete_record(...).thenReturn(
        to_async()
    )
    result = await VerifierV1.delete_proof(
        controller=mock_agent_controller, proof_id="v1-abc"
    )
    assert result is None


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [400, 500])
@pytest.mark.parametrize("error_detail", ["Error msg", "is dynamic"])
async def test_delete_proof_exception(
    mock_agent_controller: AcaPyClient, status_code: int, error_detail: str
):
    when(mock_agent_controller.present_proof_v1_0).delete_record(...).thenRaise(
        ApiException(reason=error_detail, status=status_code)
    )
    proof_id = "v1-abc"
    with pytest.raises(
        CloudApiException,
        match=f"Failed to delete record with proof id `{proof_id}`: {error_detail}.",
    ) as exc:
        await VerifierV1.delete_proof(
            controller=mock_agent_controller, proof_id=proof_id
        )

    assert exc.value.status_code == status_code


@pytest.mark.anyio
@pytest.mark.parametrize("empty_result", [True, False])
async def test_get_credentials_by_proof_id(
    mock_agent_controller: AcaPyClient, empty_result: bool
):
    when(mock_agent_controller.present_proof_v1_0).get_matching_credentials(
        ...
    ).thenReturn(
        to_async([] if empty_result else [IndyCredPrecis(cred_info=IndyCredInfo())])
    )

    creds = await VerifierV1.get_credentials_by_proof_id(
        controller=mock_agent_controller, proof_id="v1-abc"
    )

    assert isinstance(creds, list)

    if not empty_result:
        assert isinstance(creds[0], IndyCredPrecis)


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [400, 500])
@pytest.mark.parametrize("error_detail", ["Error msg", "is dynamic"])
async def test_get_credentials_by_proof_id_exception(
    mock_agent_controller: AcaPyClient, status_code: int, error_detail: str
):
    when(mock_agent_controller.present_proof_v1_0).get_matching_credentials(
        ...
    ).thenRaise(ApiException(reason=error_detail, status=status_code))
    proof_id = "v1-abc"
    with pytest.raises(
        CloudApiException,
        match=f"Failed to get credentials with proof id `{proof_id}`: {error_detail}.",
    ) as exc:
        await VerifierV1.get_credentials_by_proof_id(
            controller=mock_agent_controller, proof_id=proof_id
        )

    assert exc.value.status_code == status_code


@pytest.mark.anyio
async def test_create_proof_request_is_indy_only(mock_agent_controller: AcaPyClient):
    with pytest.raises(
        CloudApiException, match="Only Indy credential types are supported in v1."
    ) as exc:
        await VerifierV1.create_proof_request(
            controller=mock_agent_controller,
            create_proof_request=CreateProofRequest(
                type=ProofRequestType.LD_PROOF,
                protocol_version=PresentProofProtocolVersion.V1,
                dif_proof_request=DIFProofRequest(
                    presentation_definition=PresentationDefinition()
                ),
            ),
        )
    assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_send_proof_request_is_indy_only(mock_agent_controller: AcaPyClient):
    with pytest.raises(
        CloudApiException, match="Only Indy credential types are supported in v1."
    ) as exc:
        await VerifierV1.send_proof_request(
            controller=mock_agent_controller,
            send_proof_request=SendProofRequest(
                type=ProofRequestType.LD_PROOF,
                protocol_version=PresentProofProtocolVersion.V1,
                dif_proof_request=DIFProofRequest(
                    presentation_definition=PresentationDefinition()
                ),
                connection_id="abc",
            ),
        )
    assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_accept_proof_request_is_indy_only(mock_agent_controller: AcaPyClient):
    with pytest.raises(
        CloudApiException, match="Only Indy credential types are supported in v1."
    ) as exc:
        await VerifierV1.accept_proof_request(
            controller=mock_agent_controller,
            accept_proof_request=AcceptProofRequest(
                proof_id="v1-123",
                type=ProofRequestType.LD_PROOF,
                indy_presentation_spec=IndyPresSpec(
                    requested_attributes={},
                    requested_predicates={},
                    self_attested_attributes={},
                ),
            ),
        )
    assert exc.value.status_code == 400
