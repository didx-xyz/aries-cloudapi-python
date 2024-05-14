from shared.exceptions import CloudApiValueError


def cred_ex_id_no_version(cred_ex_id: str) -> str:
    if cred_ex_id.startswith("v2-") or cred_ex_id.startswith("v1-"):
        return cred_ex_id[3:]
    # else check credential id has roughly the right format
    elif len(cred_ex_id.split("-")) == 5:
        return cred_ex_id
    else:
        raise CloudApiValueError(
            "credential_exchange_id must start with prefix `v1-` or `v2-`."
        )


def strip_protocol_prefix(id: str):
    if id is None:
        return None

    if id.startswith("v1-") or id.startswith("v2-"):
        return id[3:]
    else:
        return id
