from aries_cloudcontroller import CredentialDefinition as AcaPyCredentialDefinition
from aries_cloudcontroller import ModelSchema
from assertpy import assert_that

from app.generic.definitions import (
    _credential_definition_from_acapy,
    _credential_schema_from_acapy,
)


def test_credential_schema_from_acapy():
    acapy_schema = ModelSchema(
        attr_names=["first", "second"],
        id="WgWxqztrNooG92RXvxSTWv:2:schema_name:1.1",
        seq_no=100,
        name="the_name",
        ver="1.0",
        version="1.0",
    )

    schema = _credential_schema_from_acapy(acapy_schema)

    assert_that(schema.dict()).is_equal_to(
        {
            "id": acapy_schema.id,
            "name": acapy_schema.name,
            "version": acapy_schema.version,
            "attribute_names": acapy_schema.attr_names,
        }
    )


def test_credential_definition_from_acapy():
    acapy_cred_def = AcaPyCredentialDefinition(
        schema_id="WgWxqztrNooG92RXvxSTWv:2:schema_name:1.1",
        tag="the_tag",
        id="WgWxqztrNooG92RXvxSTWv:3:CL:20:tag2",
    )

    cred_def = _credential_definition_from_acapy(acapy_cred_def)

    assert_that(cred_def.dict()).is_equal_to(
        {
            "id": acapy_cred_def.id,
            "schema_id": acapy_cred_def.schema_id,
            "tag": acapy_cred_def.tag,
        }
    )
