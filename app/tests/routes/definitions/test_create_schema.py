from unittest.mock import AsyncMock, patch

import pytest
from aries_cloudcontroller import SchemaSendRequest

from app.exceptions import CloudApiException
from app.models.definitions import CreateSchema, CredentialSchema
from app.routes.definitions import create_schema

create_schema_body = CreateSchema(
    name="Test_Schema_1", version="0.1.0", attribute_names=["attr1", "attr2"]
)
schema_send_request = SchemaSendRequest(
    attributes=["attr1", "attr2"], schema_name="Test_Schema_1", schema_version="0.1.0"
)
create_schema_response = CredentialSchema(
    id="27aG25kMFticzJ8GHH87BB:2:Test_Schema_1:0.1.0",
    name="Test_Schema_1",
    version="0.1.0",
    attribute_names=["attr1", "attr2"],
)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "request_body",
    [
        create_schema_body,
    ],
)
async def test_create_schema_success(request_body):
    mock_aries_controller = AsyncMock()
    mock_create_schema_service = AsyncMock()
    mock_create_schema_service.return_value = create_schema_response

    with patch(
        "app.routes.definitions.get_governance_controller"
    ) as mock_get_governance_controller, patch(
        "app.routes.definitions.schemas_service.create_schema",
        mock_create_schema_service,
    ):
        mock_get_governance_controller.return_value.__aenter__.return_value = (
            mock_aries_controller
        )

        response = await create_schema(
            schema=request_body, governance_auth="mocked_auth"
        )

        mock_create_schema_service.assert_called_once_with(
            aries_controller=mock_aries_controller,
            schema=request_body,
        )

        assert response == create_schema_response


@pytest.mark.anyio
@pytest.mark.parametrize(
    "expected_status_code, expected_detail",
    [
        (400, "Bad request"),
        (409, "Conflict"),
        (500, "Internal Server Error"),
    ],
)
async def test_create_schema_failure(expected_status_code, expected_detail):
    mock_aries_controller = AsyncMock()
    mock_create_schema_service = AsyncMock()

    with patch(
        "app.routes.definitions.get_governance_controller"
    ) as mock_get_governance_controller, patch(
        "app.routes.definitions.schemas_service.create_schema",
        mock_create_schema_service,
    ):
        mock_get_governance_controller.return_value.__aenter__.return_value = (
            mock_aries_controller
        )

        mock_create_schema_service.side_effect = CloudApiException(
            status_code=expected_status_code, detail=expected_detail
        )

        with pytest.raises(CloudApiException, match=expected_detail):
            await create_schema(
                schema=create_schema_body, governance_auth="mocked_auth"
            )

        mock_create_schema_service.assert_called_once_with(
            aries_controller=mock_aries_controller,
            schema=create_schema_body,
        )
