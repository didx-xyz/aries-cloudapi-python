import pytest

from assertpy import assert_that
from fastapi import HTTPException

from app.models.definitions import CredentialSchema
from app.models.tenants import CreateTenantResponse
from app.routes.trust_registry import router

from shared.constants import CLOUDAPI_URL
from shared.util.rich_async_client import RichAsyncClient

TRUST_REGISTRY = router.prefix


