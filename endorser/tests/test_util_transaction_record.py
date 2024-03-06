import json
from unittest.mock import MagicMock

import pytest
from aries_cloudcontroller import TransactionRecord

from endorser.util.transaction_record import (
    get_did_and_schema_id_from_cred_def_attachment,
    get_endorsement_request_attachment,
    is_credential_definition_transaction,
)


def test_get_endorsement_request_attachment_with_valid_attachment():
    transaction_record_with_attachment = TransactionRecord(
        messages_attach=[
            {
                "data": {
                    "json": json.dumps(
                        {
                            "identifier": "identifier_value",
                            "operation": {"type": "102", "ref": "ref_value"},
                        }
                    )
                }
            }
        ]
    )
    attachment = get_endorsement_request_attachment(transaction_record_with_attachment)
    assert attachment == {
        "identifier": "identifier_value",
        "operation": {"type": "102", "ref": "ref_value"},
    }


def test_get_endorsement_request_attachment_without_attachment():
    transaction_record_without_attachment = TransactionRecord(messages_attach=[])
    attachment = get_endorsement_request_attachment(
        transaction_record_without_attachment
    )
    assert attachment is None


def test_is_credential_definition_transaction_true():
    attachment = {"operation": {"type": "102"}}
    assert is_credential_definition_transaction(attachment) is True


def test_is_credential_definition_transaction_false():
    attachment = {"operation": {"type": "100"}}
    assert is_credential_definition_transaction(attachment) is False


@pytest.mark.anyio
async def test_get_did_and_schema_id_from_cred_def_attachment(mock_acapy_client):
    mock_acapy_client.schema.get_schema.return_value = MagicMock(
        var_schema=MagicMock(id="schema_id")
    )

    did, schema_id = await get_did_and_schema_id_from_cred_def_attachment(
        mock_acapy_client,
        {"identifier": "identifier_value", "operation": {"ref": "ref_value"}},
    )

    assert did == "did:sov:identifier_value"
    assert schema_id == "schema_id"
    mock_acapy_client.schema.get_schema.assert_awaited_once_with(schema_id="ref_value")
