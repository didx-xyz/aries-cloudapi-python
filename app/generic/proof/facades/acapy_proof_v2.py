from typing import Dict, Union, Optional

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
from aries_cloudcontroller.model.indy_proof_request import IndyProofRequest
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
        return cls.__record_to_model(proof_request)

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
        if free:
            presentation_exchange = (
                await controller.present_proof_v2_0.send_request_free(
                    body=presentation_request
                )
            )
        elif isinstance(presentation_request, AdminAPIMessageTracing) and pres_ex_id:
            presentation_exchange = await controller.present_proof_v2_0.send_request(
                pres_ex_id=pres_ex_id, body=presentation_request
            )
        elif isinstance(presentation_request, V20PresProposalRequest):
            presentation_exchange = await controller.present_proof_v2_0.send_proposal(
                body=presentation_request
            )
        else:
            raise NotImplementedError
        return cls.__record_to_model(presentation_exchange)

    @classmethod
    async def accept_proof_request(
        cls,
        controller: AcaPyClient,
        pres_ex_id: str,
        body: V20PresSpecByFormatRequest,
    ) -> PresentationExchange:
        pres_ex_id = cls.__pres_id_no_version(pres_ex_id=pres_ex_id)
        presentation_record = await controller.present_proof_v2_0.send_presentation(
            pres_ex_id=pres_ex_id, body=body
        )
        return cls.__record_to_model(presentation_record)

    @classmethod
    async def reject_proof_request(
        cls,
        controller: AcaPyClient,
        pres_ex_id: str,
        problem_report: str = None,
    ) -> None:
        # get the record
        pres_ex_id = cls.__pres_id_no_version(pres_ex_id=pres_ex_id)
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

    @classmethod
    def __pres_id_no_version(cls, pres_ex_id: str) -> str:
        if pres_ex_id.startswith("v1-") or pres_ex_id.startswith("v2-"):
            return pres_ex_id[3:]
        else:
            return pres_ex_id

    @classmethod
    def __record_to_model(cls, record: V20PresExRecord) -> PresentationExchange:
        presentation_exchange_attrs = record

        return PresentationExchange(
            auto_present=presentation_exchange_attrs.auto_present,
            connection_id=presentation_exchange_attrs.connection_id,
            created_at=presentation_exchange_attrs.created_at,
            initiator=presentation_exchange_attrs.initiator,
            presentation=presentation_exchange_attrs.pres,
            presentation_exchange_id="v2-"
            + str(presentation_exchange_attrs.pres_ex_id),
            role=presentation_exchange_attrs.role,
            state=cls.__v2_state_to_rfc_state(presentation_exchange_attrs.state),
            updated_at=presentation_exchange_attrs.updated_at,
            verified=cls.__string_to_bool(presentation_exchange_attrs.verified),
        )

    @classmethod
    def __string_to_bool(cls, verified: Optional[str]) -> Optional[bool]:
        if verified == "true":
            return True
        elif verified == "false":
            return False
        else:
            return None

    @classmethod
    def __v2_state_to_rfc_state(cls, state: Optional[str]) -> Optional[str]:
        translation_dict = {
            "proposal_sent": "proposal-sent",
            "proposal-received": "proposal-received",
            "request-sent": "request-sent",
            "request-received": "request-received",
            "presentation-sent": "presentation-sent",
            "presentation-received": "presentation-received",
            "done": "done",
            "abandoned": "abandoned",
        }

        if not state or not state in translation_dict:
            return None

        return translation_dict[state]
