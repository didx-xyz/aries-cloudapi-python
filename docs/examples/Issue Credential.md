# 5: Issuing a Credential

## Now the Issuer issues credentials

Now that a connection has been made between the `Issuer` and the `Holder`, the `Issuer` can send the credential to the `Holder` using the `connection_id` from the `Issuer's` perspective.

>Again both tenants can listen for events on the topic: `credentials`

```bash
curl -X 'POST' \
  'http://localhost:8100/generic/issuer/credentials' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: tenant.<Issuer token>' \
  -d '{
  "type": "indy",
  "indy_credential_detail": {
    "credential_definition_id": "QrHj82kaE61jnB5451zvvG:3:CL:12:Demo Person",
    "attributes": {
      "Name": "Alice",
      "Surname": "Holder",
      "Age": "25"
    }
  },
  "connection_id": "c78f9423-370e-4800-a48e-962456083943",
  "protocol_version": "v1"
}'
```

Response

```json
{
  "attributes": {
    "Name": "Alice",
    "Surname": "Holder",
    "Age": "25"
  },
  "connection_id": "c78f9423-370e-4800-a48e-962456083943",
  "created_at": "2023-11-20T09:59:29.820002Z",
  "credential_definition_id": "QrHj82kaE61jnB5451zvvG:3:CL:12:Demo Person",
  "credential_id": "v1-f126edb7-1ac1-43a3-bf1f-60b8feae4701",
  "did": null,
  "error_msg": null,
  "protocol_version": "v1",
  "role": "issuer",
  "schema_id": "FS9J6WZ6KVxwy5eGH32CgM:2:Person:0.1.0",
  "state": "offer-sent",
  "thread_id": "9ceeb941-4ebd-42ec-9ffc-ea0b7fe39722",
  "type": "indy",
  "updated_at": "2023-11-20T09:59:29.820002Z"
}
```

## Holder requests credential

Now the `Holder` needs to respond to the credential sent to him/her. Below the `Holder` is getting all it's connections. We are doing this to get the `connection_id` of the connection to the issuer. This `connection_id` can also be gotten from the `SSE events`.

```bash
curl -X 'GET' \
  'http://localhost:8100/generic/connections' \
  -H 'accept: application/json'
  -H 'x-api-key: tenant.<Holder token>'
```

Response

```json
[
  {
    "alias": "Holder <> Issuer",
    "connection_id": "ac3b0d56-eb33-408a-baeb-0370164d47ae",
    "connection_protocol": "connections/1.0",
    "created_at": "2023-11-20T09:56:41.437966Z",
    "error_msg": null,
    "invitation_key": "91ZNSpDgVoV12kHcmUqyp1JmGeKE7oGi9NFd2WMzKt4X",
    "invitation_mode": "once",
    "invitation_msg_id": "6a86e6c7-af25-4e5d-87fe-b42f559b13b9",
    "my_did": "MYhLew4uq58mou8SCTNFYp",
    "state": "completed",
    "their_did": "6wMwbinRJ5XKyBJKm7P5av",
    "their_label": "Demo Issuer",
    "their_public_did": null,
    "their_role": "inviter",
    "updated_at": "2023-11-20T09:56:41.656141Z"
  }
]
```

The `Holder` can then find the credentials offered to him/her on the `connection_id` by calling `/generic/issuer/credentials` with the optional `connection_id` query parameter.

```bash
curl -X 'GET' \
  'http://localhost:8100/generic/issuer/credentials?connection_id=ac3b0d56-eb33-408a-baeb-0370164d47ae' \
  -H 'accept: application/json'
  -H 'x-api-key: tenant.<Holder token>'
```

Response

```json
[
  {
    "attributes": {
      "Name": "Alice",
      "Surname": "Holder",
      "Age": "25"
    },
    "connection_id": "ac3b0d56-eb33-408a-baeb-0370164d47ae",
    "created_at": "2023-11-20T09:59:29.868946Z",
    "credential_definition_id": "QrHj82kaE61jnB5451zvvG:3:CL:12:Demo Person",
    "credential_id": "v1-c492cec7-2f2d-4d5f-b839-b57dcd8f8eee",
    "did": null,
    "error_msg": null,
    "protocol_version": "v1",
    "role": "holder",
    "schema_id": "FS9J6WZ6KVxwy5eGH32CgM:2:Person:0.1.0",
    "state": "offer-received",
    "thread_id": "9ceeb941-4ebd-42ec-9ffc-ea0b7fe39722",
    "type": "indy",
    "updated_at": "2023-11-20T09:59:29.868946Z"
  }
]
```

The `Holder` can now requests the credential with `credential_id` from the response above

```bash
curl -X 'POST' \
  'http://localhost:8100/generic/issuer/credentials/v1-c492cec7-2f2d-4d5f-b839-b57dcd8f8eee/request' \
  -H 'accept: application/json' \
  -H 'x-api-key: tenant.<Holder token>'
  -d ''
```

Response

```json
{
  "attributes": {
    "Name": "Alice",
    "Surname": "Holder",
    "Age": "25"
  },
  "connection_id": "ac3b0d56-eb33-408a-baeb-0370164d47ae",
  "created_at": "2023-11-20T09:59:29.868946Z",
  "credential_definition_id": "QrHj82kaE61jnB5451zvvG:3:CL:12:Demo Person",
  "credential_id": "v1-c492cec7-2f2d-4d5f-b839-b57dcd8f8eee",
  "did": null,
  "error_msg": null,
  "protocol_version": "v1",
  "role": "holder",
  "schema_id": "FS9J6WZ6KVxwy5eGH32CgM:2:Person:0.1.0",
  "state": "request-sent",
  "thread_id": "9ceeb941-4ebd-42ec-9ffc-ea0b7fe39722",
  "type": "indy",
  "updated_at": "2023-11-20T10:02:02.708045Z"
}
```

Now we listen on SSE and wait for `state` to be `done` on the `topic`: `credentials`  

```json
  {
    "wallet_id": "7bb24cc8-2e56-4326-9020-7870ad67b257",
    "topic": "credentials",
    "origin": "multitenant",
    "payload": {
      "attributes": null,
      "connection_id": "ac3b0d56-eb33-408a-baeb-0370164d47ae",
      "created_at": "2023-11-20T09:59:29.868946Z",
      "credential_definition_id": "QrHj82kaE61jnB5451zvvG:3:CL:12:Demo Person",
      "credential_id": "v1-c492cec7-2f2d-4d5f-b839-b57dcd8f8eee",
      "did": null,
      "error_msg": null,
      "protocol_version": "v1",
      "role": "holder",
      "schema_id": "FS9J6WZ6KVxwy5eGH32CgM:2:Person:0.1.0",
      "state": "done",
      "thread_id": "9ceeb941-4ebd-42ec-9ffc-ea0b7fe39722",
      "type": "indy",
      "updated_at": "2023-11-20T10:02:03.043100Z"
    }
  }
```

Once the state is done the credential will be in the `Holder's` wallet. We can list the credential in the wallet by doing the following call as the `Holder`:

```bash
curl -X 'GET' \
  'http://localhost:8100/wallet/credentials' \
  -H 'accept: application/json'
  -H 'x-api-key: tenant.<Holder token>'
```

Response

```json
{
  "results": [
    {
      "attrs": {
        "Surname": "Holder",
        "Name": "Alice",
        "Age": "25"
      },
      "cred_def_id": "QrHj82kaE61jnB5451zvvG:3:CL:12:Demo Person",
      "cred_rev_id": null,
      "referent": "86dfb6ef-1ff5-41fd-977b-092a1d97e20b",
      "rev_reg_id": null,
      "schema_id": "FS9J6WZ6KVxwy5eGH32CgM:2:Person:0.1.0"
    }
  ]
}
```

[6: Create connection with Verifier](./Create%20Connection.md)
