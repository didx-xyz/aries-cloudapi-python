# Define Your Trust Ecosystem Governance

## 1. Schemas

Schemas are used to define attributes related to credentials. To define schemas for your trust ecosystem, follow the steps below:

1. Access the API through the [Governance Cloud API](http://localhost:8000/docs).
2. Authenticate with `governance.` + `APIKEY` role.
3. Generate a new schema with a `POST` to the following API endpoint: `/generic/definitions/schemas`.

An example of a successful response to generate a DID:

```json
{
  "id": "PWmeoVrsLE2pu1idEwWFRW:2:test_schema:0.3.0",
  "name": "test_schema",
  "version": "0.3.0",
  "attribute_names": ["speed"]
}
```

## 2. Creating Tenants

Creating new tenants in the multi-tenant environment for the various tenant types in the Trust Ecosystem:

### Issuers

Tenants are custodial wallets created within the Trust Ecosystem's multitenant AcaPy agent. To create new tenants for your trust ecosystem, follow the steps below:

1. Access the API through the [Governance Cloud API](http://localhost:8000/docs).
2. Authenticate with `tenant-admin.` + `APIKEY` role.
3. Create a new tenant with a `POST` to the following API endpoint: `/admin/tenants/`, using the example request body below.

```json
{
  "image_url": "https://www.abc.xyz/assets/images/logo/logo.png",
  "name": "Issuer",
  "roles": ["issuer"]
}
```

An example of a successful response to create a new Issuer Tenant:

```json
{
  "access_token": "tenant.eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ3YWxsZXRfaWQiOiIzNTM3NmU0Yy1lYTI5LTQ1MDAtYTBhZC0xMGY3NTBkZGExM2UifQ.DEoMAD4AhLF-gHfr8JdqiRnZl31RltFIWk-al30F9Ak",
  "wallet_id": "35376e4c-ea29-4500-a0ad-10f750dda13e",
  "wallet_label": "Issuer",
  "image_url": "https://www.abc.xyz/assets/images/logo/logo.png",
  "created_at": "2022-06-07T07:53:12.584044Z",
  "updated_at": "2022-06-07T07:53:12.584044Z"
}
```

### Verifiers

Tenants, functioning as custodial wallets, are established within the Trust Ecosystem's multitenant AcaPy agent. Follow the steps below to create new tenants for your trust ecosystem:

1. Access the API through [Governance Cloud API](http://localhost:8000/docs)
2. Authenticate using the `tenant-admin.`+`APIKEY` role
3. Generate a new tenant with a `POST` request to the API endpoint `/admin/tenants/` using the request body detailed in the example below

   ```json
   {
     "image_url": "https://www.abc.xyz/assets/images/logo/logo.png",
     "name": "Verifier",
     "roles": ["verifier"]
   }
   ```

4. Below is an example of a successful response to the creation of a new Verifier Tenant:

   ```json
   {
     "access_token": "tenant.eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ3YWxsZXRfaWQiOiIxOTkwYzkzNS1iNTFlLTQ0NjMtODQ0Ny1hMGFmMzFlNDRlNDIifQ.SqmG9--tCLgJ1FV_31uc4yVOchX_t7oc7jHyVKq8W3w",
     "wallet_id": "1990c935-b51e-4463-8447-a0af31e44e42",
     "wallet_label": "Verifier",
     "image_url": "https://www.abc.xyz/assets/images/logo/logo.png",
     "created_at": "2022-06-07T07:56:45.045014Z",
     "updated_at": "2022-06-07T07:56:45.045014Z"
   }
   ```

### Holders

Similar to Verifiers, Tenants for Holders are created within the Trust Ecosystem's multitenant AcaPy agent. Follow these steps to create new Holders for your trust ecosystem:

1. Access the API through [Governance Cloud API](http://localhost:8000/docs)
2. Authenticate using `tenant-admin.`+`APIKEY` role
3. Generate a new tenant with a `POST` to the API endpoint `/admin/tenants/` using the request body in the example below

   ```json
   {
     "image_url": "https://www.abc.xyz/assets/images/logo/logo.png",
     "name": "Holder"
   }
   ```

4. Here is an example of a successful response to creating a new Holder Tenant:

   ```json
   {
     "access_token": "tenant.eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ3YWxsZXRfaWQiOiJjZmFmMjc2ZS1jZTc2LTQxMTYtYmUwZC03YTU0OWQ2NDgwNWIifQ.eQNCRQvKuNSlelUNZuDGpUPK7Dtvgo3uO4gDorZd2I4",
     "wallet_id": "cfaf276e-ce76-4116-be0d-7a549d64805b",
     "wallet_label": "Holder",
     "image_url": "https://www.abc.xyz/assets/images/logo/logo.png",
     "created_at": "2022-06-07T07:58:22.043147Z",
     "updated_at": "2022-06-07T07:58:22.043147Z"
   }
   ```

## 3. Credential Definitions

Credential definitions are expected to be created by all **_Issuers_** within the trust ecosystem who wish to issue credentials to holders. The Trust Authority, which administers the trust ecosystem and enables tenants to write to the Indy Ledger, acts as the `Transaction Endorser` of the Trust Ecosystem. Meanwhile, Issuers serve as `Transaction Authors` within the Trust Ecosystem. For additional information on `Transaction Endorsers` and `Transaction Authors`, please refer to [Aries Transaction Endorser Support](https://github.com/hyperledger/aries-cloudagent-python/blob/main/Endorser.md).

To create credential definitions through the `Transaction Endorser Protocol` for trust ecosystem _issuers_, follow the steps below:

1. Access the API through [Governance Cloud API](http://localhost:8000/docs)
2. Authenticate as an Issuer using `tenant.`+`JWTKey` role
3. Create a new schema with a `POST` to the API endpoint `/generic/definitions/credentials` using the request body illustrated in the example below.

   > NOTE: The schema ID should already exist in the ledger and be accessible in the Trust Registry

   ```json
   {
     "tag": "default",
     "schema_id": "JPqFhPEM4UiR2ZNK9CM4NA:2:test_schema:0.3.0"
   }
   ```

4. Below is an example of a successful response to writing a credential definition:

   ```json
   {
     "id": "EfFA6wi7fcZNWzRuHeQqaj:3:CL:8:default",
     "tag": "default",
     "schema_id": "JPqFhPEM4UiR2ZNK9CM4NA:2:test_schema:0.3.0"
   }
   ```

## 4. Trust Registry

To query entries in the Trust Registry, adhere to the following steps:

1. Access the API through [Governance Cloud API](http://localhost:8000/docs)
2. Authenticate as an Issuer using `tenant.`+`JWTKey` role

   > NOTE: The Trust Registry is currently public and accessible to anyone on the internet

3. Generate a new schema by issuing a `GET` request to the API endpoint `/trust-registry/`.
4. The following is an example of a successful response to writing a credential definition:

```json
{
  "actors": [
    {
      "id": "35376e4c-ea29-4500-a0ad-10f750dda13e",
      "name": "Issuer",
      "roles": ["issuer"],
      "did": "did:sov:EfFA6wi7fcZNWzRuHeQqaj",
      "didcomm_invitation": null
    },
    {
      "id": "1990c935-b51e-4463-8447-a0af31e44e42",
      "name": "Verifier",
      "roles": ["verifier"],
      "did": "did:key:z6Mkp7xg3iTDHa9gqhx3y7kjWTBCAGYpSQR4W2Ddgbk6jT3P",
      "didcomm_invitation": "http://localhost:4020?oob=eyJAdHlwZSI6ICJkaWQ6c292OkJ6Q2JzTlloTXJqSGlxWkRUVUFTSGc7c3BlYy9vdXQtb2YtYmFuZC8xLjAvaW52aXRhdGlvbiIsICJAaWQiOiAiNTgwYmQyMDctNmM2MC00M2Q0LWI4M2EtMTliMTE3YTMzNWI5IiwgInNlcnZpY2VzIjogW3siaWQiOiAiI2lubGluZSIsICJ0eXBlIjogImRpZC1jb21tdW5pY2F0aW9uIiwgInJlY2lwaWVudEtleXMiOiBbImRpZDprZXk6ejZNa3A3eGczaVRESGE5Z3FoeDN5N2tqV1RCQ0FHWXBTUVI0VzJEZGdiazZqVDNQIl0sICJzZXJ2aWNlRW5kcG9pbnQiOiAiaHR0cDovL3NzaS5kaWR4LmNvLnphOjQwMjAifV0sICJoYW5kc2hha2VfcHJvdG9jb2xzIjogWyJkaWQ6c292OkJ6Q2JzTlloTXJqSGlxWkRUVUFTSGc7c3BlYy9kaWRleGNoYW5nZS8xLjAiXSwgImxhYmVsIjogIlZlcmlmaWVyIn0="
    }
  ],
  "schemas": [
    "SHYDM4P2P5LiRz44nNZa9f:2:test schema:1.0",
    "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
    "PWmeoVrsLE2pu1idEwWFRW:2:test_schema:0.3.0",
    "PWmeoVrsLE2pu1idEwWFRW:2:DIDx_Member:0.1.0",
    "JPqFhPEM4UiR2ZNK9CM4NA:2:test_schema:0.3.0"
  ]
}
```
