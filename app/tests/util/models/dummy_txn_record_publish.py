txn_record = {
    "state": "request_sent",
    "created_at": "2024-07-16T07:09:37.807261Z",
    "updated_at": "2024-07-16T07:09:37.812035Z",
    "trace": False,
    "transaction_id": "667f76bf-f950-4dd6-a2f2-b84a3b39b5e1",
    "_type": "https://didcomm.org/sign-attachment/1.0/signature-request",
    "signature_request": [
        {
            "context": "did:sov",
            "method": "add-signature",
            "signature_type": "default",
            "signer_goal_code": "aries.transaction.endorse",
            "author_goal_code": "aries.transaction.ledger.write",
        }
    ],
    "signature_response": [],
    "timing": {"expires_time": None},
    "formats": [
        {
            "attach_id": "dbeb9942-fe14-4960-a242-cdc469495ee8",
            "format": "dif/endorse-transaction/request@v1.0",
        }
    ],
    "messages_attach": [
        {
            "@id": "dbeb9942-fe14-4960-a242-cdc469495ee8",
            "mime-type": "application/json",
            "data": {
                "json": {
                    "endorser": "CYJnoJA7fDaz6hWoDP4nj7",
                    "identifier": "WYbzsbG3Nzx9ME3AC9poTD",
                    "operation": {
                        "revocDefType": "CL_ACCUM",
                        "revocRegDefId": "WYbzsbG3Nzx9ME3AC...d-1c69a9309c9c",
                        "type": "114",
                        "value": {
                            "accum": "...",
                            "prevAccum": "...",
                            "revoked": [7],
                        },
                    },
                    "protocolVersion": 2,
                    "reqId": 1721113777802885400,
                    "signature": "3KtmzZt2WnQTWXqmLJ...ZMYbzemwPgz7QgxUSfAU3f",
                    "taaAcceptance": {
                        "mechanism": "service_agreement",
                        "taaDigest": "0be4d87dec17a...ccc078f",
                        "time": 1721088000,
                    },
                }
            },
        }
    ],
    "meta_data": {"context": {}, "processing": {}},
    "connection_id": "64753329-ec71-4b19-b2e0-ee6c6e5a5cfd",
    "endorser_write_txn": False,
}
