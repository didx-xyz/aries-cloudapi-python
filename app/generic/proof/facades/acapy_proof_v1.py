from typing import Dict, Union
import logging

from aries_cloudcontroller import (
    AcaPyClient,
    IndyPresSpec,
    IndyProofRequest,
    V10PresentationCreateRequestRequest,
    V10PresentationProblemReportRequest,
    V10PresentationProposalRequest,
    V10PresentationSendRequestRequest,
)
from aries_cloudcontroller.model.v10_presentation_exchange import (
    V10PresentationExchange,
)
from fastapi.exceptions import HTTPException
from pydantic.typing import NoneType

from app.generic.proof.facades.acapy_proof import Proof
import app.generic.proof.facades.acapy_proof_utils as utils
from app.generic.proof.models import PresentationExchange

logger = logging.getLogger(__name__)


class ProofsV1(Proof):
    @classmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: IndyProofRequest,
        comment: str = None,
    ) -> V10PresentationExchange:
        presentation_exchange = (
            await controller.present_proof_v1_0.create_proof_request(
                body=V10PresentationCreateRequestRequest(
                    proof_request=proof_request,
                    comment=comment,
                    trace=False,
                )
            )
        )
        return utils.record_to_model(presentation_exchange)

    @classmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: Union[
            V10PresentationSendRequestRequest,
            V10PresentationProposalRequest,
        ],
        free: bool = True,
        proof_id: str = None,
    ) -> PresentationExchange:
        try:
            # This "free" is de facto the only one we support right now
            if free and isinstance(proof_request, V10PresentationSendRequestRequest):
                presentation_exchange = (
                    await controller.present_proof_v1_0.send_request_free(
                        body=V10PresentationSendRequestRequest(**proof_request.dict())
                    )
                )
            elif isinstance(proof_request, V10PresentationProposalRequest):
                presentation_exchange = (
                    await controller.present_proof_v1_0.send_proposal(
                        body=proof_request
                    )
                )
            else:
                raise NotImplementedError
            return utils.record_to_model(presentation_exchange)
        except Exception as e:
            raise e from e

    @classmethod
    async def accept_proof_request(
        cls,
        controller: AcaPyClient,
        proof_id: str,
        body: IndyPresSpec,
    ) -> PresentationExchange:
        proof_id = utils.pres_id_no_version(proof_id=proof_id)
        presentation_record = await controller.present_proof_v1_0.send_presentation(
            pres_ex_id=proof_id, body=body
        )
        return utils.record_to_model(presentation_record)

    @classmethod
    async def reject_proof_request(
        cls,
        controller: AcaPyClient,
        proof_id: str,
        problem_report: str = None,
    ) -> None:
        # get the record
        proof_id = utils.pres_id_no_version(proof_id=proof_id)
        proof_request = await controller.present_proof_v1_0.get_record(
            pres_ex_id=proof_id
        )
        # Report problem if desired
        if problem_report:
            try:
                await controller.present_proof_v1_0.report_problem(
                    pres_ex_id=proof_id,
                    body=V10PresentationProblemReportRequest(
                        description=problem_report
                    ),
                )
            except Exception as e:
                raise e from e
        # delete exchange record
        delete_proof_request_res = await controller.present_proof_v1_0.delete_record(
            pres_ex_id=proof_id
        )
        if not isinstance(proof_request, V10PresentationExchange) or not isinstance(
            delete_proof_request_res, (Dict, NoneType)
        ):
            raise HTTPException(status_code=500, detail="Failed to delete record")
