## 4: Create Connection

Now that the Issuer has a credential definition, he can start issuing credentials. However in order to do that, he firts needs to create a connection to the holder. There are multiple ways to create connections. We will use the `/generic/connections/` endpoints in these examples.

## Create connection between Issuer and Holder

As the `Issuer` we create a connection.

>Note: The `multi_use` field indicates that the `invitation object/url` can be sent to multiple tenants to create connections with them.

```bash
curl -X 'POST' \
  'http://localhost:8100/generic/connections/create-invitation' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: tenant.<Issuer token>' \
  -d '{
  "alias": "Issuer <> Holder",
  "multi_use": false,
  "use_public_did": false
}'
```

Response

```json
{
  "connection_id": "c78f9423-370e-4800-a48e-962456083943",
  "invitation": {
    "@id": "6a86e6c7-af25-4e5d-87fe-b42f559b13b9",
    "@type": "https://didcomm.org/connections/1.0/invitation",
    "did": null,
    "imageUrl": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
    "label": "Demo Issuer",
    "recipientKeys": [
      "91ZNSpDgVoV12kHcmUqyp1JmGeKE7oGi9NFd2WMzKt4X"
    ],
    "routingKeys": null,
    "serviceEndpoint": "http://governance-multitenant-agent:3020"
  },
  "invitation_url": "http://governance-multitenant-agent:3020?c_i=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL2Nvbm5lY3Rpb25zLzEuMC9pbnZpdGF0aW9uIiwgIkBpZCI6ICI2YTg2ZTZjNy1hZjI1LTRlNWQtODdmZS1iNDJmNTU5YjEzYjkiLCAic2VydmljZUVuZHBvaW50IjogImh0dHA6Ly9nb3Zlcm5hbmNlLW11bHRpdGVuYW50LWFnZW50OjMwMjAiLCAiaW1hZ2VVcmwiOiAiaHR0cHM6Ly91cGxvYWQud2lraW1lZGlhLm9yZy93aWtpcGVkaWEvY29tbW9ucy83LzcwL0V4YW1wbGUucG5nIiwgInJlY2lwaWVudEtleXMiOiBbIjkxWk5TcERnVm9WMTJrSGNtVXF5cDFKbUdlS0U3b0dpOU5GZDJXTXpLdDRYIl0sICJsYWJlbCI6ICJEZW1vIElzc3VlciJ9"
}
```

The `Holder` accepts the connection by using the invitation object above.

```bash
curl -X 'POST' \
  'http://localhost:8100/generic/connections/accept-invitation' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: tenant.<Holder token>' \
  -d '{
  "alias": "Holder <> Issuer",
  "use_existing_connection": false,
  "invitation": {
    "@id": "6a86e6c7-af25-4e5d-87fe-b42f559b13b9",
    "@type": "https://didcomm.org/connections/1.0/invitation",
    "did": null,
    "imageUrl": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
    "label": "Demo Issuer",
    "recipientKeys": [
      "91ZNSpDgVoV12kHcmUqyp1JmGeKE7oGi9NFd2WMzKt4X"
    ],
    "routingKeys": null,
    "serviceEndpoint": "http://governance-multitenant-agent:3020"
  }
}'
```

Response

```json
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
  "state": "request-sent",
  "their_did": null,
  "their_label": "Demo Issuer",
  "their_public_did": null,
  "their_role": "inviter",
  "updated_at": "2023-11-20T09:56:41.472385Z"
}
```

Both of the tenants can listen to `Webhook/SSE events` to track the progress of the connection being made. Once the `state` is `completed` the connection is made. Below is an example of a sse event at the `completed` state.

>NOTE: The field IDs will be unique to each tenant i.e. the `connection_id` of the `Issuer` will be different from that of the `Holder`, even though they refer to the same connection.

```json
{
    "wallet_id": "4e0c70fb-f2ad-4f59-81f3-93d8df9b977a",
    "topic": "connections",
    "origin": "multitenant",
    "payload": {
      "alias": "Holder <> Issuer",
      "connection_id": "359b30a2-c98d-4c00-b318-8185d1d0e64d",
      "connection_protocol": "connections/1.0",
      "created_at": "2023-11-16T07:57:18.451554Z",
      "error_msg": null,
      "invitation_key": "8Vd5YSVBw5p6BJ8nHngZ2UcCKBmTSxQHoNWfaBQJXW5U",
      "invitation_mode": "once",
      "invitation_msg_id": "0ef82415-20ba-4d1e-818b-92a70355ec6e",
      "my_did": "NXk4JkDpFff4MpnTwvn1Wa",
      "state": "completed",
      "their_did": "LN2WMyrMFH74L1GTkSteka",
      "their_label": "Demo Issuer",
      "their_public_did": null,
      "their_role": "inviter",
      "updated_at": "2023-11-16T07:57:18.748560Z"
    }
  }
```

### Now we can [5: Issue a Credential](Issue%20Credential.md)

>We will create a connection with the verifier later.

***

## 6: Create connection between Verifier and Holder

Again we first create a `connection`. This time between the `Verifier` and `Holder`.

```bash
curl -X 'POST' \
  'http://localhost:8100/generic/connections/create-invitation' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "alias": "Verifier <> Holder",
  "multi_use": false,
  "use_public_did": false
}'
```

Response

```json
{
  "connection_id": "30f0c10e-b8d6-4609-8a13-fca96b2ff00f",
  "invitation": {
    "@id": "4a68ed4b-6a86-45e2-95e9-a76edcd93bc4",
    "@type": "https://didcomm.org/connections/1.0/invitation",
    "did": null,
    "imageUrl": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
    "label": "Demo Verifier",
    "recipientKeys": [
      "Cn3rHufXa94xCUKoSGseXinFSn6oNBb543n15NE6mLzJ"
    ],
    "routingKeys": null,
    "serviceEndpoint": "http://governance-multitenant-agent:3020"
  },
  "invitation_url": "http://governance-multitenant-agent:3020?c_i=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL2Nvbm5lY3Rpb25zLzEuMC9pbnZpdGF0aW9uIiwgIkBpZCI6ICI0YTY4ZWQ0Yi02YTg2LTQ1ZTItOTVlOS1hNzZlZGNkOTNiYzQiLCAic2VydmljZUVuZHBvaW50IjogImh0dHA6Ly9nb3Zlcm5hbmNlLW11bHRpdGVuYW50LWFnZW50OjMwMjAiLCAiaW1hZ2VVcmwiOiAiaHR0cHM6Ly91cGxvYWQud2lraW1lZGlhLm9yZy93aWtpcGVkaWEvY29tbW9ucy83LzcwL0V4YW1wbGUucG5nIiwgInJlY2lwaWVudEtleXMiOiBbIkNuM3JIdWZYYTk0eENVS29TR3NlWGluRlNuNm9OQmI1NDNuMTVORTZtTHpKIl0sICJsYWJlbCI6ICJEZW1vIFZlcmlmaWVyIn0="
}
```

The `Holder` `accepts` the invitation

```bash
curl -X 'POST' \
  'http://localhost:8100/generic/connections/accept-invitation' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "alias": "Holder <> Verifier",
  "use_existing_connection": false,
  "invitation": {
    "@id": "4a68ed4b-6a86-45e2-95e9-a76edcd93bc4",
    "@type": "https://didcomm.org/connections/1.0/invitation",
    "did": null,
    "imageUrl": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
    "label": "Demo Verifier",
    "recipientKeys": [
      "Cn3rHufXa94xCUKoSGseXinFSn6oNBb543n15NE6mLzJ"
    ],
    "routingKeys": null,
    "serviceEndpoint": "http://governance-multitenant-agent:3020"
  }
}'
```

Response

```json
{
  "alias": "Holder <> Verifier",
  "connection_id": "bc8f43aa-5c02-401d-86a0-45d6d08f94b8",
  "connection_protocol": "connections/1.0",
  "created_at": "2023-11-20T10:06:01.683789Z",
  "error_msg": null,
  "invitation_key": "Cn3rHufXa94xCUKoSGseXinFSn6oNBb543n15NE6mLzJ",
  "invitation_mode": "once",
  "invitation_msg_id": "4a68ed4b-6a86-45e2-95e9-a76edcd93bc4",
  "my_did": "CnjLLG4U5RPbrYHG4cTMWw",
  "state": "request-sent",
  "their_did": null,
  "their_label": "Demo Verifier",
  "their_public_did": null,
  "their_role": "inviter",
  "updated_at": "2023-11-20T10:06:01.721340Z"
}
```

Listen to SSE until `state`: `completed`

```json
  {
    "wallet_id": "7bb24cc8-2e56-4326-9020-7870ad67b257",
    "topic": "connections",
    "origin": "multitenant",
    "payload": {
      "alias": "Holder <> Verifier",
      "connection_id": "bc8f43aa-5c02-401d-86a0-45d6d08f94b8",
      "connection_protocol": "connections/1.0",
      "created_at": "2023-11-20T10:06:01.683789Z",
      "error_msg": null,
      "invitation_key": "Cn3rHufXa94xCUKoSGseXinFSn6oNBb543n15NE6mLzJ",
      "invitation_mode": "once",
      "invitation_msg_id": "4a68ed4b-6a86-45e2-95e9-a76edcd93bc4",
      "my_did": "CnjLLG4U5RPbrYHG4cTMWw",
      "state": "completed",
      "their_did": "2guow2rkGp9wESxZPEWPSJ",
      "their_label": "Demo Verifier",
      "their_public_did": null,
      "their_role": "inviter",
      "updated_at": "2023-11-20T10:06:01.922033Z"
    }
  }
```

[Verify Issued Credential](./Verify%20Credential.md)
