from typing import Any, Optional

from aries_cloudcontroller import (
    AttachDecorator,
    AttachDecoratorData,
    IndyPresAttrSpec,
    IndyPresPredSpec,
    IndyPresPreview,
    IndyPresSpec,
    IndyProof,
    IndyProofProof,
    IndyProofRequest,
    IndyProofRequestedProof,
    IndyRequestedCredsRequestedPred,
    IndyRequestedCredsRequestedAttr,
    V10PresentationExchange,
    V10PresentationProposalRequest,
    V20Pres,
    V20PresExRecord,
    V20PresExRecordByFormat,
    V20PresFormat,
    V20PresProposal,
    V20PresRequestByFormat,
)


# need this to handle the async with the mock
async def get(response: Optional[Any] = None):
    if response:
        return response


indy_proof = IndyProof(
    identifiers=[],
    proof=IndyProofProof(aggregated_proof=None, proofs=None),
    requested_proof=IndyProofRequestedProof(),
)

indy_proof_request = IndyProofRequest(
    name=None,
    non_revoked=None,
    nonce=None,
    requested_attributes=None,
    requested_predicates=None,
    version="0.0.1",
)

v10_presentation_exchange_records = [
    V10PresentationExchange(
        auto_present=False,
        connection_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        created_at="2021-09-15 13:49:47Z",
        error_msg=None,
        initiator="self",
        presentation=indy_proof,
        presentation_exchange_id="dabc8f4e-164a-410f-bd10-471b090f65a5",
        presentation_proposal_dict=None,
        presentation_request=indy_proof_request,
        presentation_request_dict=None,
        role="prover",
        state=None,
        thread_id=None,
        trace=False,
        updated_at=None,
        verified="false",
    ),
]

v10_presentation_proposal_request = V10PresentationProposalRequest(
    connection_id="xyz",
    presentation_proposal=IndyPresPreview(
        attributes=[IndyPresAttrSpec(name="abc")],
        predicates=[IndyPresPredSpec(name="abc", predicate=">", threshold=1)],
    ),
    auto_present=True,
)

proof_dict = dict(
    {
        "connection_id": "string",
        "proof_request": {
            "name": "string",
            "non_revoked": {"from_": 0, "to": 0},
            "nonce": "12345",
            "requested_attributes": {
                "0_string_uuid": {
                    "name": "string",
                    "names": ["string"],
                    "non_revoked": {"from_": 0, "to": 0},
                    "restrictions": None,
                },
            },
            "requested_predicates": {
                "0_string_GE_uuid": {
                    "name": "string",
                    "p_type": "<",
                    "p_value": 0,
                    "non_revoked": {"from_": 0, "to": 0},
                    "restrictions": None,
                },
            },
            "version": "0.1",
        },
        "comment": "string",
        "trace": True,
    }
)

v20_presentation_exchange_records = [
    V20PresExRecord(
        auto_present=False,
        by_format=V20PresExRecordByFormat(
            pres={},
            pres_proposal={},
            pres_request={},
        ),
        connection_id="abc",
        created_at="2021-09-15 13:49:47Z",
        error_msg=None,
        initiator="self",
        pres=V20Pres(
            formats=[V20PresFormat(attach_id="1234", format="indy")],
            presentationsattach=[
                AttachDecorator(
                    data=AttachDecoratorData(base64="kjbdvjbvekjvo"),
                )
            ],
            pres_ex_id="abcd",
            pres_proposal=V20PresProposal(
                formats=[V20PresFormat(attach_id="1234", format="indy")],
                proposalsattach=[
                    AttachDecorator(
                        data=AttachDecoratorData(base64="kjbdvjbvekjvo"),
                    )
                ],
            ),
        ),
        pres_request=None,
        role="prover",
        state=None,
        thread_id=None,
        trace=None,
        updated_at=None,
        verified="false",
    ),
]

proof_request_indy = V20PresRequestByFormat(
    dif=None,
    indy=IndyProofRequest(**proof_dict),
)


indy_pres_spec = IndyPresSpec(
    requested_attributes={
        "0_string_uuid": IndyRequestedCredsRequestedAttr(cred_id="0_string_uuid")
    },
    requested_predicates={
        "0_string_GE_uuid": IndyRequestedCredsRequestedPred(cred_id="0_string_GE_uuid")
    },
    self_attested_attributes={"sth": "sth_else"},
)
