from typing import Dict, Union

from aries_cloudcontroller import (
    AcaPyClient,
    AdminAPIMessageTracing,
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
from app.generic.proof.models import PresentationExchange


class ProofsV2(Proof):
    @classmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof: V20PresRequestByFormat,
        comment: str = None,
        trace: bool = False,
    ) -> PresentationExchange:

        proof_request = await controller.present_proof_v2_0.create_proof_request(
            body=V20PresCreateRequestRequest(
                presentation_request=proof,
                comment=comment,
                trace=trace,
            )
        )

        return PresentationExchange(v20=proof_request)

    @classmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        presentation_request: Union[
            V20PresSendRequestRequest, AdminAPIMessageTracing, V20PresProposalRequest
        ],
        free: bool = True,
        pres_ex_id: str = None,
    ) -> PresentationExchange:
        try:
            if free:
                presentation_exchange = (
                    await controller.present_proof_v2_0.send_request_free(
                        body=V20PresSendRequestRequest(**presentation_request.dict())
                    )
                )
            elif (
                isinstance(presentation_request, AdminAPIMessageTracing) and pres_ex_id
            ):
                presentation_exchange = (
                    await controller.present_proof_v2_0.send_request(
                        pres_ex_id=pres_ex_id, body=presentation_request
                    )
                )
            elif isinstance(presentation_request, V20PresProposalRequest):
                presentation_exchange = (
                    await controller.present_proof_v2_0.send_proposal(
                        body=presentation_request
                    )
                )
            else:
                raise NotImplementedError
            return PresentationExchange(v20=presentation_exchange)
        except Exception as e:
            raise e from e

    @classmethod
    async def accept_proof_request(
        cls,
        controller: AcaPyClient,
        pres_ex_id: str,
        body: V20PresSpecByFormatRequest = None,
    ) -> PresentationExchange:
        presentation_record = await controller.present_proof_v2_0.send_presentation(
            pres_ex_id=pres_ex_id, body=body
        )

        return PresentationExchange(v20=presentation_record)

    @classmethod
    async def reject_proof_request(
        cls,
        controller: AcaPyClient,
        pres_ex_id: str,
        problem_report: str = None,
    ) -> None:
        # get the record
        proof_request = await controller.present_proof_v2_0.get_record(
            pres_ex_id=pres_ex_id
        )
        # Report problem if desired
        if problem_report:
            try:
                await controller.present_proof_v2_0.report_problem(
                    pres_ex_id=pres_ex_id,
                    body=V20PresProblemReportRequest(description=problem_report),
                )
            except Exception as e:
                raise e from e
        # delete exchange record
        delete_proof_request_res = await controller.present_proof_v2_0.delete_record(
            pres_ex_id=pres_ex_id
        )
        if not isinstance(proof_request, V20PresExRecord) or not isinstance(
            delete_proof_request_res, (Dict, NoneType)
        ):
            raise HTTPException(status_code=500, detail="Failed to delete record")
