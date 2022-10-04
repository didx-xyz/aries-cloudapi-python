def did_from_credential_definition_id(credential_definition_id: str) -> str:
    parts = credential_definition_id.split(":")

    return parts[0]
