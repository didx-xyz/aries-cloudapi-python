from typing import Dict, Optional, Union

from aries_cloudcontroller import (
    AcaPyClient,
    AdminAPIMessageTracing,
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
from app.generic.proof.models import PresentationExchange


class ProofsV1(Proof):
    @classmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof: IndyProofRequest,
        comment: str = None,
        trace: bool = False,
    ) -> V10PresentationExchange:

        proof_request = await controller.present_proof_v1_0.create_proof_request(
            body=V10PresentationCreateRequestRequest(
                proof_request=proof,
                comment=comment,
                trace=trace,
            )
        )

        return PresentationExchange(v10=proof_request)

    @classmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        presentation_request: Union[
            V10PresentationSendRequestRequest,
            AdminAPIMessageTracing,
            V10PresentationProposalRequest,
        ],
        free: bool = False,
        pres_ex_id: str = None,
    ) -> V10PresentationExchange:
        try:
            # This "free" is de facto the only one we support right now
            if free:
                presentation_exchange = (
                    await controller.present_proof_v1_0.send_request_free(
                        body=presentation_request
                    )
                )
            elif (
                isinstance(presentation_request, AdminAPIMessageTracing) and pres_ex_id
            ):
                presentation_exchange = (
                    await controller.present_proof_v1_0.send_request(
                        pres_ex_id=pres_ex_id, body=presentation_request
                    )
                )
            elif isinstance(presentation_request, V10PresentationProposalRequest):
                presentation_exchange = (
                    await controller.present_proof_v1_0.send_proposal(
                        body=presentation_request
                    )
                )
            else:
                raise NotImplementedError
            return PresentationExchange(v10=presentation_exchange)
        except Exception as e:
            raise e from e

    @classmethod
    async def accept_proof_request(
        cls,
        controller: AcaPyClient,
        pres_ex_id: str,
        body: Optional[IndyPresSpec] = {},
    ) -> PresentationExchange:
        presentation_record = await controller.present_proof_v1_0.send_presentation(
            pres_ex_id=pres_ex_id, body=body
        )
        return PresentationExchange(v10=presentation_record)

    @classmethod
    async def reject_proof_request(
        cls,
        controller: AcaPyClient,
        pres_ex_id: str,
        problem_report: str = None,
    ) -> None:
        # get the record
        proof_request = await controller.present_proof_v1_0.get_record(
            pres_ex_id=pres_ex_id
        )
        # Report problem if desired
        if problem_report:
            try:
                await controller.present_proof_v1_0.report_problem(
                    pres_ex_id=pres_ex_id,
                    body=V10PresentationProblemReportRequest(
                        description=problem_report
                    ),
                )
            except Exception as e:
                raise e from e
        # delete exchange record
        delete_proof_request_res = await controller.present_proof_v1_0.delete_record(
            pres_ex_id=pres_ex_id
        )
        if not isinstance(proof_request, V10PresentationExchange) or not isinstance(
            delete_proof_request_res, (Dict, NoneType)
        ):
            raise HTTPException(status_code=500, detail="Failed to delete record")
