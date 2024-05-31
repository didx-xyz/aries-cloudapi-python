import pytest
from aries_cloudcontroller import IndyPresSpec
from fastapi import HTTPException

from app.routes.verifier import AcceptProofRequest, router
from app.tests.util.connections import AcmeAliceConnect
from app.tests.util.verifier import send_proof_request
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient
from shared.models.credential_exchange import CredentialExchange
from shared.models.presentation_exchange import PresentationExchange

VERIFIER_BASE_PATH = router.prefix
