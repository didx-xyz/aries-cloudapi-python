from typing import Union

from aries_cloudcontroller import (
    AcaPyClient,
    IndyProofRequest,
    V20PresCreateRequestRequest,
    V20PresExRecord,
    V20PresSendRequestRequest,
    AdminAPIMessageTracing,
    V20PresProposalRequest,
    V20PresSpecByFormatRequest,
    V20PresProblemReportRequest,
)
from fastapi.exceptions import HTTPException

from generic.proof.facades.acapy_proof import Proof
from generic.proof.models import Presentation


class ProofsV2(Proof):
    @classmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof: IndyProofRequest,
        comment: str = None,
        trace: bool = False,
    ) -> Presentation:

        proof_request = await controller.present_proof_v2_0.create_proof_request(
            body=V20PresCreateRequestRequest(
                proof_request=proof,
                comment=comment,
                trace=trace,
            )
        )

        return cls.__presentation_to_model(proof_request)

    @classmethod
    async def send_proof_request(
        cls,
        controller: AcaPyClient,
        presentation_request: Union[
            V20PresSendRequestRequest, AdminAPIMessageTracing, V20PresProposalRequest
        ],
        free: bool = False,
        pres_ex_id: str = None,
    ) -> Presentation:
        try:
            if free:
                presentation_exchange = (
                    await controller.present_proof_v2_0.send_request_free(
                        body=V20PresSendRequestRequest
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
            return cls.__presentation_to_model(presentation_exchange)
        except Exception as e:
            raise e from e

    @classmethod
    async def accept_proof_request(
        cls,
        controller: AcaPyClient,
        pres_ex_id: str,
        body: V20PresSpecByFormatRequest = None,
    ) -> Presentation:
        presentation_record = await controller.present_proof_v2_0.send_presentation(
            pres_ex_id=pres_ex_id, body=body
        )

        return cls.__presentation_to_model(presentation_record)

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
        deleted_request_record = await controller.present_proof_v2_0.get_record(
            pres_ex_id=pres_ex_id
        )
        if (
            not isinstance(proof_request, V20PresExRecord)
            or not isinstance(delete_proof_request_res, dict)
            or proof_request == deleted_request_record
        ):
            raise HTTPException(status_code=500, detail="Failed to delete record")

    @classmethod
    def __presentation_to_model(cls, presentation: V20PresExRecord):

        # Instead of declaring all attributes explicitly, just fill in the ones we have
        # Using spread operator and the rest should default to None or declaration is invalid
        presentation_record = Presentation(**presentation.dict())
        # To distinguish v10 and v20 overwrite presentation_exchange_id and prepend v10 to key
        # This is in order to be consistent with issuer formatting in this repo
        # There already is distinguishment between v10: credential_exchange_id
        # and v20: cred_ex_id etc
        presentation_record.presentation_exchange_id = (
            f"v2-{presentation.presentation_exchange_id}"
        )
        return presentation_record
