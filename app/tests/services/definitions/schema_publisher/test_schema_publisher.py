from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aries_cloudcontroller import (
    ModelSchema,
    SchemaGetResult,
    SchemaSendRequest,
    SchemaSendResult,
    TxnOrSchemaSendResult,
)

from app.exceptions import CloudApiException
from app.models.definitions import CredentialSchema
from app.services.definitions.schema_publisher import SchemaPublisher


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def mock_controller():
    return AsyncMock()


@pytest.fixture
def publisher(mock_controller, mock_logger):
    return SchemaPublisher(mock_controller, mock_logger)


@pytest.mark.anyio
async def test_publish_schema_success(publisher):
    mock_schema_request = MagicMock(spec=SchemaSendRequest)
    mock_result = TxnOrSchemaSendResult(
        sent=SchemaSendResult(
            schema_id="CXQseFxV34pcb8vf32XhEa:2:test_schema:1.0",
            var_schema=ModelSchema(
                id="CXQseFxV34pcb8vf32XhEa:2:test_schema:1.0",
                name="test_schema",
                version="1.0",
                attr_names=["attr1", "attr2"],
            ),
        )
    )
    final_result = CredentialSchema(
        id="CXQseFxV34pcb8vf32XhEa:2:test_schema:1.0",
        name="test_schema",
        version="1.0",
        attribute_names=["attr1", "attr2"],
    )
    with patch(
        "app.services.definitions.schema_publisher.handle_acapy_call",
        return_value=mock_result,
    ), patch(
        "app.services.definitions.schema_publisher.register_schema"
    ) as mock_register_schema:
        result = await publisher.publish_schema(mock_schema_request)

        assert result == final_result
        mock_register_schema.assert_called_once_with(
            schema_id="CXQseFxV34pcb8vf32XhEa:2:test_schema:1.0"
        )


@pytest.mark.anyio
async def test_publish_schema_already_exists(publisher):
    mock_schema_request = MagicMock(spec=SchemaSendRequest)
    mock_existing_schema = CredentialSchema(
        id="CXQseFxV34pcb8vf32XhEa:2:test_schema:1.0",
        name="test_schema",
        version="1.0",
        attribute_names=["attr1", "attr2"],
    )

    with patch(
        "app.services.definitions.schema_publisher.handle_acapy_call",
        side_effect=[
            CloudApiException(detail="already exist", status_code=400),
            mock_existing_schema,
        ],
    ), patch.object(
        publisher, "_handle_existing_schema", return_value=mock_existing_schema
    ):
        result = await publisher.publish_schema(mock_schema_request)

        assert result == mock_existing_schema


@pytest.mark.anyio
async def test_publish_schema_unhandled_exception(publisher):
    mock_schema_request = MagicMock(spec=SchemaSendRequest)

    with patch(
        "app.services.definitions.schema_publisher.handle_acapy_call",
        side_effect=CloudApiException(detail="Unhandled error", status_code=500),
    ):
        with pytest.raises(CloudApiException) as exc_info:
            await publisher.publish_schema(mock_schema_request)

        assert "Error while creating schema." in str(exc_info.value)


@pytest.mark.anyio
async def test_publish_schema_no_schema_id(publisher):
    mock_schema_request = MagicMock(spec=SchemaSendRequest)
    mock_result = TxnOrSchemaSendResult(sent=None)

    with patch(
        "app.services.definitions.schema_publisher.handle_acapy_call",
        return_value=mock_result,
    ):
        with pytest.raises(CloudApiException) as exc_info:
            await publisher.publish_schema(mock_schema_request)

        assert "An unexpected error occurred: could not publish schema." in str(
            exc_info.value
        )


@pytest.mark.anyio
async def test_handle_existing_schema_success(publisher):
    mock_schema_request = SchemaSendRequest(
        schema_name="test_schema",
        schema_version="1.0",
        attributes=["attr1", "attr2"],
    )
    mock_pub_did = MagicMock()
    mock_pub_did.result.did = "test_did"

    mock_schema = SchemaGetResult(
        var_schema=ModelSchema(
            id="CXQseFxV34pcb8vf32XhEa:2:test_schema:1.0",
            name="test_schema",
            version="1.0",
            attr_names=["attr1", "attr2"],
        )
    )
    with patch(
        "app.services.definitions.schema_publisher.handle_acapy_call",
        side_effect=[mock_pub_did, mock_schema],
    ), patch(
        "app.services.definitions.schema_publisher.credential_schema_from_acapy",
        return_value=MagicMock(spec=CredentialSchema),
    ):
        result = await publisher._handle_existing_schema(mock_schema_request)

        assert isinstance(result, CredentialSchema)


@pytest.mark.anyio
async def test_handle_existing_schema_different_attributes(publisher):
    mock_schema_request = SchemaSendRequest(
        schema_name="test_schema", schema_version="1.0", attributes=["attr1", "attr2"]
    )
    mock_pub_did = MagicMock()
    mock_pub_did.result.did = "test_did"

    mock_schema = SchemaGetResult(
        var_schema=ModelSchema(
            attr_names=["attr1", "attr3"],
            id="CXQseFxV34pcb8sss2XhEa:2:test_schema:1.0",
            name="test_schema",
            version="1.0",
        )
    )
    with patch(
        "app.services.definitions.schema_publisher.handle_acapy_call",
        side_effect=[mock_pub_did, mock_schema],
    ):
        with pytest.raises(CloudApiException) as exc_info:
            await publisher._handle_existing_schema(mock_schema_request)

        assert "Schema already exists with different attribute names" in str(
            exc_info.value
        )


@pytest.mark.anyio
async def test_handle_existing_schema_changed_did(publisher):
    mock_schema_request = SchemaSendRequest(
        schema_name="test_schema", schema_version="1.0", attributes=["attr1", "attr2"]
    )
    mock_pub_did = MagicMock()
    mock_pub_did.result.did = "test_did"

    mock_schema_none = SchemaGetResult(var_schema=None)
    mock_schemas_created_ids = MagicMock()
    mock_schemas_created_ids.schema_ids = ["schema_id_1"]

    mock_schema = SchemaGetResult(
        var_schema=ModelSchema(
            attr_names=["attr1", "attr2"],
            id="CXQseFxV34pcb8sss2XhEa:2:test_schema:1.0",
            name="test_schema",
            version="1.0",
        )
    )
    with patch(
        "app.services.definitions.schema_publisher.handle_acapy_call",
        side_effect=[
            mock_pub_did,
            mock_schema_none,
            mock_schemas_created_ids,
            mock_schema,
        ],
    ), patch(
        "app.services.definitions.schema_publisher.credential_schema_from_acapy",
        return_value=MagicMock(spec=CredentialSchema),
    ):
        result = await publisher._handle_existing_schema(mock_schema_request)

        assert isinstance(result, CredentialSchema)


@pytest.mark.anyio
async def test_handle_existing_schema_no_schemas_found(publisher):
    mock_schema_request = MagicMock(spec=SchemaSendRequest)
    mock_schema_request.schema_name = "test_schema"
    mock_schema_request.schema_version = "1.0"
    mock_schema_request.attributes = ["attr1", "attr2"]

    mock_pub_did = MagicMock()
    mock_pub_did.result.did = "test_did"

    mock_schema_none = MagicMock(spec=SchemaGetResult)
    mock_schema_none.var_schema = None

    mock_schemas_created_ids = MagicMock()
    mock_schemas_created_ids.schema_ids = []

    with patch(
        "app.services.definitions.schema_publisher.handle_acapy_call",
        side_effect=[mock_pub_did, mock_schema_none, mock_schemas_created_ids],
    ):
        with pytest.raises(CloudApiException) as exc_info:
            await publisher._handle_existing_schema(mock_schema_request)

        assert str(exc_info.value) == "500: Could not publish schema."
        assert exc_info.value.status_code == 500


# @pytest.mark.anyio
# async def test_handle_existing_schema_multiple_schemas_found(publisher):
#     mock_schema_request = MagicMock(spec=SchemaSendRequest)
#     mock_schema_request.schema_name = "test_schema"
#     mock_schema_request.schema_version = "1.0"
#     mock_schema_request.attributes = ["attr1", "attr2"]

#     mock_pub_did = MagicMock()
#     mock_pub_did.result.did = "test_did"

#     mock_schema_none = MagicMock(spec=SchemaGetResult)
#     mock_schema_none.var_schema = None

#     mock_schemas_created_ids = MagicMock()
#     mock_schemas_created_ids.schema_ids = ["CXQseFxV34pcb8vf32XhEa:2:test_schema:1.0", "aeXh23fv8bp43VxFesQXC:2:test_schema:1.0"]
#     mock_schemas = [
#         SchemaGetResult(
#             var_schema=ModelSchema(
#                 id="CXQseFxV34pcb8vf32XhEa:2:test_schema:1.0",
#                 name="test_schema",
#                 version="1.0",
#                 attr_names=["attr1", "attr2"],
#             )
#         ),
#         SchemaGetResult(
#             var_schema=ModelSchema(
#                 id="aeXh23fv8bp43VxFesQXC:2:test_schema:1.0",
#                 name="test_schema",
#                 version="1.0",
#                 attr_names=["attr3", "attr4"],
#             )
#         )
#     ]
#     with patch(
#         "app.services.definitions.schema_publisher.handle_acapy_call",
#         side_effect=[
#             mock_pub_did,
#             mock_schema_none,
#             mock_schemas_created_ids,
#         ],
#     ):
#         with pytest.raises(CloudApiException) as exc_info:
#             await publisher._handle_existing_schema(mock_schema_request)

#         assert (
#             str(exc_info.value)
#             == "409: Multiple schemas with name test_schema and version 1.0 exist. These are: `['schema_id_1', 'schema_id_2']`."
#         )
#         assert exc_info.value.status_code == 409
