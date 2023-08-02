from aries_cloudcontroller import CredentialDefinition as AcaPyCredentialDefinition
from aries_cloudcontroller import ModelSchema

from app.models.definitions import CredentialDefinition, CredentialSchema


def credential_schema_from_acapy(schema: ModelSchema):
    return CredentialSchema(
        id=schema.id,
        name=schema.name,
        version=schema.version,
        attribute_names=schema.attr_names,
    )


def credential_definition_from_acapy(credential_definition: AcaPyCredentialDefinition):
    return CredentialDefinition(
        id=credential_definition.id,
        tag=credential_definition.tag,
        schema_id=credential_definition.schema_id,
    )
