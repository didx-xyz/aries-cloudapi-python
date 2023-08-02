def cred_id_no_version(credential_id: str) -> str:
    if credential_id.startswith("v2-") or credential_id.startswith("v1-"):
        return credential_id[3:]
    # else check credential id has roughly the right format
    elif len(credential_id.split("-")) == 5:
        return credential_id
    else:
        raise ValueError("credential_id must start with prefix `v1-` or `v2-`.")


def strip_protocol_prefix(id: str):
    if id.startswith("v1-") or id.startswith("v2-"):
        return id[3:]
    else:
        return id
