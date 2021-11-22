from gettext import translation
from typing import Dict, Optional, Union
import logging
import json

from pydantic import ValidationError
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

logger = logging.getLogger(__name__)


class ProofsV1(Proof):
    @classmethod
    async def create_proof_request(
        cls,
        controller: AcaPyClient,
        proof: IndyProofRequest,
        comment: str = None,
        trace: bool = False,
    ) -> V10PresentationExchange:
        presentation_exchange = (
            await controller.present_proof_v1_0.create_proof_request(
                body=V10PresentationCreateRequestRequest(
                    proof_request=proof,
                    comment=comment,
                    trace=trace,
                )
            )
        )
        return cls.__record_to_model(presentation_exchange)

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
    ) -> PresentationExchange:
        try:
            # This "free" is de facto the only one we support right now
            if free:
                presentation_exchange = (
                    await controller.present_proof_v1_0.send_request_free(
                        body=V10PresentationSendRequestRequest(
                            **presentation_request.dict()
                        )
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
            return cls.__record_to_model(presentation_exchange)
        except Exception as e:
            raise e from e

    @classmethod
    async def accept_proof_request(
        cls,
        controller: AcaPyClient,
        pres_ex_id: str,
        body: IndyPresSpec,
    ) -> PresentationExchange:
        pres_ex_id = cls.__pres_id_no_version(pres_ex_id=pres_ex_id)
        presentation_record = await controller.present_proof_v1_0.send_presentation(
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

    @classmethod
    def __pres_id_no_version(cls, pres_ex_id: str) -> str:
        if pres_ex_id.startswith("v1-") or pres_ex_id.startswith("v2-"):
            return pres_ex_id[3:]
        else:
            return pres_ex_id

    @classmethod
    def __record_to_model(cls, record: V10PresentationExchange) -> PresentationExchange:
        # When createing rewuest instead of sending
        if not record.presentation:
            record.presentation = record.presentation_request_dict.dict()

        return PresentationExchange(
            auto_present=record.auto_present,
            connection_id=record.connection_id,
            created_at=record.created_at,
            initiator=record.initiator,
            presentation=record.presentation,
            presentation_exchange_id="v1-" + str(record.presentation_exchange_id),
            role=record.role,
            state=cls.__v1_state_to_rfc_state(record.state),
            updated_at=record.updated_at,
            verified=cls.__string_to_bool(record.verified),
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
    def __v1_state_to_rfc_state(cls, state: Optional[str]) -> Optional[str]:
        translation_dict = {
            "proposal_sent": "proposal-sent",
            "proposal_received": "proposal-received",
            "request_sent": "request-sent",
            "request_received": "request-received",
            "presentation_sent": "presentation-sent",
            "presentation_received": "presentation-received",
            "done": "done",
            "abandoned": "abandoned",
        }

        if not state or not state in translation_dict:
            return None

        return translation_dict[state]
