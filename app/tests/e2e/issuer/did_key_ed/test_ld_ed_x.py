from copy import deepcopy

import pytest
from aries_cloudcontroller import Credential, LDProofVCDetail, LDProofVCDetailOptions
from assertpy import assert_that
from fastapi import HTTPException

from app.models.issuer import SendCredential
from app.routes.issuer import router as issuer_router
from app.tests.util.ecosystem_connections import FaberAliceConnect
from app.tests.util.trust_registry import DidKey
from shared import RichAsyncClient

CREDENTIALS_BASE_PATH = issuer_router.prefix

credential_ = SendCredential(
    type="ld_proof",
    connection_id="",
    protocol_version="v2",
    ld_credential_detail=LDProofVCDetail(
        credential=Credential(
            context=[
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            type=["VerifiableCredential", "UniversityDegreeCredential"],
            credentialSubject={
                "degree": {
                    "type": "BachelorDegree",
                    "name": "Bachelor of Science and Arts",
                },
                "college": "Faber College",
            },
            issuanceDate="2021-04-12",
            issuer="",
        ),
        options=LDProofVCDetailOptions(proofType="Ed25519Signature2018"),
    ),
).model_dump(by_alias=True, exclude_unset=True)

# This is the json of the above credential
# {
#     "type": "ld_proof",
#     "connection_id": "",
#     "protocol_version": "v2",
#     "ld_credential_detail": {
#         "credential": {
#             "@context": [
#                 "https://www.w3.org/2018/credentials/v1",
#                 "https://www.w3.org/2018/credentials/examples/v1",
#             ],
#             "type": ["VerifiableCredential", "UniversityDegreeCredential"],
#             "credentialSubject": {
#                 "degree": {
#                     "type": "BachelorDegree",
#                     "name": "Bachelor of Science and Arts",
#                 },
#                 "college": "Faber College",
#             },
#             "issuanceDate": "2021-04-12",
#             "issuer": "",
#         },
#         "options": "",
#     },
# }
