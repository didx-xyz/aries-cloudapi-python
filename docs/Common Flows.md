## Common Steps

This document will guide you through some common flows and interactions. Please read it carefully and feel free to open an issue if further questions arise or you spotted a mistake.

NOTE: It is always handy to look at the CloudAPI Swagger UI to inspect what endpoints are available, what the expected inputs are and what you will receive in return. If requests fail, please, check in the Swagger UI whether you have actually called the correct endpoint with the correct data. Under vanilla setup the Swagger UI lives under [http://localhost:8000/docs](http://localhost:8000/docs). If you feel like some datatype is unclear from below document try finding it out in SwaggerUI before opening an issue. This documents only describes some basic flows and interactions. Not every possible flow or interaction can or will be covered in docs. It is therefore good to learn to consult the SwaggerUI as a reference and solve things independently.

It is also recommended to set up a webhook listener (see also `webhooks.md`). This will help you significantly in following what is happening in teh aca-py instances in the background.

### Creating wallets

The admin "wallet" is already configured because it is not a subwallet on a multitenant agent. In order to create subwallets for tenants you have to use the `tenant-admin` role. The permissions to do so and routing to the correct aca-py instance are handled by the CLoudAPI under the hood. You have to provide two things here:

1. authorization in header `{"x-api-key": "tenant-admin.TENANT_ADMIN_ACAPY_API_KEY"}` where `tenant-admin` is a fixed term representing the role and `TENANT_ADMIN_ACAPY_API_KEY` is the auth token you have to know and provide. NOTE: This auth string is separated by a dot so keep that in there.
2. The wallet payload (body) of the wallet you want to create e.g.:

   ```json
   {
     "image_url": "https://yoma.africa/images/sample.png",
     "name": "governance",
     "roles": ["issuer"]
   }
   ```

Send this against the `/admin/tenants` endpoint (under standard spin up this will be [http://localhost:8000](http://localhost:8000)). You can omit the roles field altogether or pass "issuer" and/or "verifier". Again, all payloads are documented in Swagger so if in doubt you can navigate to the [Swagger docs](http://localhost:8000/docs) by adding `/docs` to the CloudAPI main endpoint. This will also update the trustregistry by writing an entry to the `actors` field about the wallet and its associated roles.

If you wish to later on update entities roles you will have to do that also via the tenants API which will handle interacting with the trustregistry (see also the Swagger for `update tenant`).

### Creating schemas

In order to create schemas and effectively writing them to the ledger as well as registering it on the trustregistry use the governance role by

1. providing the following authentication header:

   ```bash
     {"x-api-key": "governance.GOVERNANCE_ACAPY_API_KEY"}
   ```

   and replace the `GOVERNANCE_ACAPY_API_KEY` with the actual api key. As mentioned above keep the dot and the `governance` is a keyword known to the CloudAPI as a role. It will resolve the correct endpoint and available actions based on the role and provided token. And:

2. Providing the information about the schema e.g. :
   ```json
   {
     "name": "yourAwesomeSchemaName",
     "version": "4.2.0",
     "attributes": ["skill", "age"]
   }
   ```
   Note that you will have to have a public DID to do so (if your agent lacks one you can use the governance role and create one providing the same auth header as described in this step; see SWAGGER). Run the request with the header from 1. and the payload from 2. against the CloudAPI url and endpoint `/admin/governance/schemas/` (POST method). On success the created schema will be returned.

### Issuing a credential

#### Outline

1.  Register a schema (see above)
2.  Register an issuer (see above)
    1. In other words, create a wallet passing "issuer" as a role
3.  Create a connection between issuer and prospect holder

    1. Create an invitation using either the issuer or the holder using the `/connections` endpoint of the CloudAPI. Here you will also need to authenticate via the header e.g. using

       ```json
       { "x-api-key": "tenant.WALLET_TOKEN" }
       ```

       where the `WALLET_TOKEN` is the bearer token you get from the create wallet response for a tenant wallet.

    2. Copy the content `invitation` field from the create invitation response and use it as the payload in the `accept-invitation` endpoint and post to the CloudAPI using the other entity. To illustrate, if you used the issuer to create the invitation use the holder for this call and vice versa. Again register using the headers appropriately.

4.  Issue credential from issuer to prospect holder

    1.  Create and send a credential authenticating with the issuer. The credential has the form:

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

        and should correspond to a schema you have created previously and the `connection_id` is the id of the connection you have created in the previous step. If you are unsure what that id is you can always run a GET request against the `connections` endpoint to find it.

5.  Accept and store credential holder wallet
6.  Using the holder (authenticating with the holder auth header) issue a GET request against the `/generic/issuer/credentials` endpoint providing the connection ID of the connection established above. NOTE: The connection IDs are unique for each entity so the connection between the issuer and the holder is one connection with two separate connection IDs - one for the issuer and one for the holder. This will provide you with a credential record that should be in state offered. Providing the connection ID again you can now use the holder to store the credential by posting to `/generic/issuer/credentials/{credential_id}/store`
7.  (Optional) Repeat the GETting your credential records using the holder and check whether credential is actually stored. You can also check this via the webhooks.

### Verifying a credential

#### Outline

1.  Ensure you followed **Issue credential** steps to have a wallet with a credential (prover)
2.  Register an entity as a verifier (verifier)
    1. In other words, create or update a passing the role "verifier"
3.  Create a connection between 1. prover and 2. verifier the same way as in **Issue credential**
4.  Create a proof request (`/generic/verifier/create-request`) using the verifier and send it to the prover. Here consult the Swagger `verifier` endpoints. POST to `/generic/verifier/send-request` with a payload of the following form replacing the values accordingly (and ensuring they can be covered by the previously created schema and issued credential):

    ```json
      {
        "protocol_version": "v1",
        "connection_id": "string",
        "proof_request": {
        "requested_attributes": {
        "additionalProp1": {
          "name": "string",
          "names": [
            "string"
          ],
          "non_revoked": {
            "from": 0,
            "to": 0
          },
          "restrictions": []
          },
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
          "non_revoked": {
          },
          "version": "string"
        }
      }
    ```

5.  Send the proof request.

    1. From the prover get the proof records using `/generic/verifier/proofs` and create a proof request you want to send just as above (same payload format and endpoint)

6.  Accept the proof request

    1. From the verifier you can now accept (or reject; `/generic/verifier/reject-request` - see Swagger for payload by POSTing to `/generic/verifier/send-request` with adjusting the payload of:

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

7.  (Optional) look through 1. prover's and 2. verifier's webhooks and see that the presentation is acknowledged. Or GET the proof records and check the `state` field.

NOTE: There are multiple flows this "dance" can be "danced". For further details you may want to refer to the corresponding [official aries-rfc](https://github.com/hyperledger/aries-rfcs/tree/main/features/0037-present-proof).
