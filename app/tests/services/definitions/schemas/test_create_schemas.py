from unittest.mock import AsyncMock, patch

import pytest
from aries_cloudcontroller import SchemaSendRequest

from app.exceptions import CloudApiException
from app.models.definitions import CreateSchema, CredentialSchema
from app.services.definitions.schemas import create_schema


@pytest.mark.anyio
async def test_create_schema_success():
    # Mock the necessary dependencies
    mock_aries_controller = AsyncMock()
    mock_aries_controller.configuration.host = "http://governance-agent-url"

    mock_schema_publisher = AsyncMock()
    mock_schema_publisher.publish_schema.return_value = CredentialSchema(
        id="CXQseFxV34pcb8vf32XhEa:2:test_schema:0.3.0",
        name="test_schema",
        version="0.3.0",
        attribute_names=["attr1", "attr2"],
    )

    # Create a sample CreateSchema object
    create_schema_payload = CreateSchema(
        name="test_schema", version="0.3.0", attribute_names=["attr1", "attr2"]
    )

    # Patch the necessary functions and classes
    with patch(
        "app.services.definitions.schemas.GOVERNANCE_AGENT_URL",
        "http://governance-agent-url",
    ), patch(
        "app.services.definitions.schemas.SchemaPublisher",
        return_value=mock_schema_publisher,
    ), patch(
        "app.services.definitions.schemas.handle_model_with_validation"
    ) as mock_handle_model:

        # Set up the mock for handle_model_with_validation
        mock_handle_model.return_value = SchemaSendRequest(
            schema_name="test_schema",
            schema_version="1.0",
            attributes=["attr1", "attr2"],
        )

        # Call the function
        result = await create_schema(mock_aries_controller, create_schema_payload)

        # Assertions
        assert isinstance(result, CredentialSchema)
        assert result.id == "CXQseFxV34pcb8vf32XhEa:2:test_schema:0.3.0"
        assert result.name == "test_schema"
        assert result.version == "0.3.0"
        assert result.attribute_names == ["attr1", "attr2"]

        mock_schema_publisher.publish_schema.assert_called_once()
        mock_handle_model.assert_called_once()


@pytest.mark.anyio
async def test_create_schema_non_governance_agent():
    mock_aries_controller = AsyncMock()
    mock_aries_controller.configuration.host = "http://non-governance-agent-url"

    create_schema_payload = CreateSchema(
        name="test_schema", version="1.0", attribute_names=["attr1", "attr2"]
    )

    with patch(
        "app.services.definitions.schemas.GOVERNANCE_AGENT_URL",
        "http://governance-agent-url",
    ):
        with pytest.raises(CloudApiException) as exc_info:
            await create_schema(mock_aries_controller, create_schema_payload)

        assert exc_info.value.status_code == 403
        assert "Only governance agents are allowed to access this endpoint." in str(
            exc_info.value
        )
