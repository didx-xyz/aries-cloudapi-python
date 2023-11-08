import pytest
from app.models.definitions import CredentialSchema

from app.event_handling.sse_listener import SseListener
from app.routes.admin.tenants import router
from app.routes.connections import router as conn_router
from app.routes.definitions import router as def_router
from app.routes.issuer import router as issuer_router

from app.tests.util.client import get_tenant_client
from shared import RichAsyncClient

TENANTS_BASE_PATH = router.prefix
CONNECTIONS_BASE_PATH = conn_router.prefix
DEFINITIONS_BASE_PATH = def_router.prefix
ISSUER_BASE_PATH = issuer_router.prefix

