# Common Flows

This document will guide you through some common flows and interactions. Please read it carefully, and feel free to open an issue if further questions arise or you spot a mistake.

> **Note:** It is always helpful to inspect the CloudAPI Swagger UI to understand the available endpoints, their expected inputs, and the corresponding outputs. If requests fail, check the Swagger UI to ensure you've called the correct endpoint with the correct data. The Swagger UI is accessible at [http://localhost:8000/docs](http://localhost:8000/docs) under a vanilla setup. If you find any datatype unclear from the document below, try finding it in SwaggerUI before opening an issue. This document describes only some basic flows and interactions; not every possible flow or interaction can be covered. Thus, learning to consult the SwaggerUI as a reference and solving issues independently is beneficial.

It is also recommended to set up a webhook listener (refer to `webhooks.md`). This will significantly aid in understanding the activities occurring in the ACA-Py instances in the background.

## Creating Wallets

The admin "wallet" is already configured as it is not a subwallet on a multi-tenant agent. To create subwallets for tenants, you have to use the member admin role. The permissions and routing to the correct ACA-Py instance are handled by the CloudAPI under the hood. You need to provide two things:

1. Authorization in the header: `{"x-api-key": "member-admin.MEMBER_ACAPY_API_KEY"}`, where `member-admin` is a fixed term representing the role, and `MEMBER_ACAPY_API_KEY` is the auth token you must know and provide. _Note: This auth string is separated by a dot, so keep that in there._
2. The wallet payload (body) of the wallet you want to create, e.g.,

   ```json
   {
     "image_url": "https://yoma.africa/images/sample.png",
     "name": "governance",
     "roles": ["issuer"]
   }
   ```

Send this to the `/admin/tenants` endpoint (under standard spin up this will be [http://localhost:8000](http://localhost:8000)). You can omit the roles field altogether or pass "issuer" and/or "verifier". All payloads are documented in Swagger, so if in doubt, navigate to the [Swagger docs](http://localhost:8000/docs) by adding `/docs` to the CloudAPI main endpoint. This will also update the trust registry by writing an entry to the `actors` field about the wallet and its associated roles.

If you wish to later update entities roles, you will have to do that also via the tenants API, which will handle interacting with the trust registry (see also the Swagger for `update tenant`).

## Creating Schemas

To create schemas and effectively write them to the ledger as well as registering them on the trust registry, use the governance role:

1. Provide the following authentication header:

   ```json
   { "x-api-key": "governance.ADMIN_API_KEY" }
   ```

   Replace the `ADMIN_API_KEY` with the actual API key. Keep the dot and understand that `governance` is a keyword known to the CloudAPI as a role. It will resolve the correct endpoint and available actions based on the role and provided token.

2. Provide the information about the schema, e.g. :

   ```json
   {
     "name": "yourAwesomeSchemaName",
     "version": "4.2.0",
     "attributes": ["skill", "age"]
   }
   ```

   Note that you will need to have a public DID to do so (if your agent lacks one, you can use the governance role and create one, providing the same auth header as described in this step; see SWAGGER). Run the request with the header from 1. and the payload from 2. against the CloudAPI URL and endpoint `/admin/governance/schemas/` (POST method). Upon success, the created schema will be returned.

## Issuing a Credential

1. Register a schema (see above)
2. Register an issuer (see above)
   1. In other words, create a wallet passing "issuer" as a role
3. Create a connection between the issuer and prospect holder

   1. Create an invitation using either the issuer or the holder using the `/connections` endpoint of the CloudAPI. Here, you will also need to authenticate via the header, e.g., using

      ```json
      { "x-api-key": "member.WALLET_TOKEN" }
      ```

      where the `WALLET_TOKEN` is the bearer token you get from the create wallet response for a tenant wallet.

   2. Copy the content `invitation` field from the create invitation response and use it as the payload in the `accept-invitation` endpoint, and post to the CloudAPI using the other entity. To illustrate, if you used the issuer to create the invitation, use the holder for this call and vice versa. Again, register using the headers appropriately.

4. Issue a credential from issuer to prospect holder

   1. Create and send a credential authenticating with the issuer. The credential has the form:

   ```json
   {
     "protocol_version": "v1",
     "connection_id": "string",
     "schema_id": "string",
     "attributes": {
       "additionalProp1": "string",
       "additionalProp2": "string",
       "additionalProp3": "string"
     }
   }
   ```

   This should correspond to a schema you created previously, and the `connection_id` is the ID of the connection you created in the previous step. If you're unsure what that ID is, you can always run a GET request against the `connections` endpoint to find it.

5. Accept and store the credential in the holder wallet
6. Using the holder (authenticating with the holder auth header), issue a GET request against the `/generic/issuer/credentials` endpoint, providing the connection ID of the connection established above. _Note: The connection IDs are unique for each entity, so the connection between the issuer and the holder is one connection with two separate connection IDs - one for the issuer and one for the holder._ This will provide you with a credential record that should be in the state of being offered. Providing the connection ID again, you can now use the holder to store the credential by posting to `/generic/issuer/credentials/{credential_id}/store`
7. (Optional) Repeat the GETting of your credential records using the holder and check whether the credential is actually stored. You can also check this via the webhooks.

## Verifying a Credential

1. Ensure you followed **Issuing a Credential** steps to have a wallet with a credential (prover)
2. Register an entity as a verifier (verifier)
   1. In other words, create or update a wallet, passing the role "verifier"
3. Create a connection between 1. prover and 2. verifier the same way as in **Issuing a Credential**
4. Create a proof request (`/generic/verifier/create-request`) using the verifier and send it to the prover. Consult the Swagger `verifier` endpoints. POST to `/generic/verifier/send-request` with a payload of the following form, replacing the values accordingly (and ensuring they can be covered by the previously created schema and issued credential):

   ```json
   {
     "protocol_version": "v1",
     "connection_id": "string",
     "proof_request": {
       "requested_attributes": {
         "additionalProp1": {
           "name": "string",
           "names": ["string"],
           "non_revoked": {
             "from": 0,
             "to": 0
           },
           "restrictions": []
         }
       },
       "requested_predicates": {
         "additionalProp1": {
           "name": "string",
           "p_type": "<",
           "p_value": 0,
           "non_revoked": {
             "from": 0,
             "to": 0
           },
           "restrictions": []
         },
         "name": "string",
         "non_revoked": {},
         "version": "string"
       }
     }
   }
   ```

5. Send the proof request.

   1. From the prover, get the proof records using `/generic/verifier/proofs` and create a proof request you want to send, just as above (same payload format and endpoint).

6. Accept the proof request.

   1. From the verifier, you can now accept (or reject; see `/generic/verifier/reject-request` on Swagger for payload) by POSTing to `/generic/verifier/send-request`, adjusting the payload to:

   ```json
   {
     "protocol_version": "v1",
     "proof_id": "string",
     "presentation_spec": {
       "requested_attributes": {
         "additionalProp1": {
           "cred_id": "string",
           "revealed": true
         }
       },
       "requested_predicates": {
         "additionalProp1": {
           "cred_id": "string",
           "timestamp": 0
         }
       },
       "self_attested_attributes": {
         "additionalProp1": "string",
         "additionalProp2": "string",
         "additionalProp3": "string"
       },
       "trace": false
     }
   }
   ```

7. (Optional) Look through 1. prover's and 2. verifier's webhooks and see that the presentation is acknowledged. Alternatively, GET the proof records and check the `state` field.

_Note: There are multiple flows this "dance" can be "danced". For further details, you may want to refer to the corresponding [official Aries-RFC](https://github.com/hyperledger/aries-rfcs/tree/main/features/0037-present-proof)._
