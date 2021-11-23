from typing import Dict, Union

from aries_cloudcontroller import (
    AcaPyClient,
    V20PresCreateRequestRequest,
    V20PresExRecord,
    V20PresProblemReportRequest,
    V20PresProposalRequest,
    V20PresRequestByFormat,
    V20PresSendRequestRequest,
    V20PresSpecByFormatRequest,
)
from fastapi.exceptions import HTTPException
from pydantic.typing import NoneType

from app.generic.proof.facades.acapy_proof import Proof
import app.generic.proof.facades.acapy_proof_utils as utils
from app.generic.proof.models import PresentationExchange


class ProofsV2(Proof):
    @classmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: V20PresRequestByFormat,
        comment: str = None,
    ) -> PresentationExchange:

        proof_request = await controller.present_proof_v2_0.create_proof_request(
            body=V20PresCreateRequestRequest(
                presentation_request=proof_request,
                comment=comment,
                trace=False,
            )
        )
        return utils.record_to_model(proof_request)

    @classmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        proof_request: Union[V20PresSendRequestRequest, V20PresProposalRequest],
        free: bool = True,
    ) -> PresentationExchange:
        if free and isinstance(proof_request, V20PresSendRequestRequest):
            presentation_exchange = (
                await controller.present_proof_v2_0.send_request_free(
                    body=proof_request
                )
            )
        elif isinstance(proof_request, V20PresProposalRequest):
            presentation_exchange = await controller.present_proof_v2_0.send_proposal(
                body=proof_request
            )
        else:
            raise NotImplementedError
        return utils.record_to_model(presentation_exchange)

    @classmethod
    async def accept_proof_request(
        cls,
        controller: AcaPyClient,
        proof_id: str,
        body: V20PresSpecByFormatRequest,
    ) -> PresentationExchange:
        proof_id = utils.pres_id_no_version(proof_id=proof_id)
        presentation_record = await controller.present_proof_v2_0.send_presentation(
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
        proof_request = await controller.present_proof_v2_0.get_record(
            pres_ex_id=proof_id
        )
        # Report problem if desired
        if problem_report:
            try:
                await controller.present_proof_v2_0.report_problem(
                    pres_ex_id=proof_id,
                    body=V20PresProblemReportRequest(description=problem_report),
                )
            except Exception as e:
                raise e from e
        # delete exchange record
        delete_proof_request_res = await controller.present_proof_v2_0.delete_record(
            pres_ex_id=proof_id
        )
        if not isinstance(proof_request, V20PresExRecord) or not isinstance(
            delete_proof_request_res, (Dict, NoneType)
        ):
            raise HTTPException(status_code=500, detail="Failed to delete record")
