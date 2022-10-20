# Define your Trust Ecosystem Governance
## 1. Schemas
Schemas are used to define attributes related to credentials.  
To define schemas for your trust ecosystem follow the steps below:
1. Access the API through [Governance Cloud API](http://localhost:8000/docs)
2. Authenticate with `governance.`+`APIKEY` role 
3. Generate a new schema with a `POST` to the following API endpoint `/generic/definitions/schemas`
4. An example successful response to generate a DID

```json
  {
    "id": "PWmeoVrsLE2pu1idEwWFRW:2:test_schema:0.3.0",
    "name": "test_schema",
    "version": "0.3.0",
    "attribute_names": [
      "speed"
    ]
  }
```
## 2. Creating Tenants
Creating new tenants in the multi-tenant environment for the various tenant types in the Trust Ecosystem.

### Issuers
Tenants are custodial wallets that are created inside the Trust Ecosystem multitenant AcaPy agent.
To create new tenants for your trust ecosystem follow the steps below:
1. Access the API through [Governance Cloud API](http://localhost:8000/docs)
2. Authenticate with `tenant-admin.`+`APIKEY` role 
3. Create a new tenant with a `POST` to the following API endpoint `/admin/tenants/` with the request body as example below
```json
{
  "image_url": "https://www.abc.xyz/assets/images/logo/logo.png",
  "name": "Issuer",
  "roles": [ "issuer"]
}
```
4. An example successful response to create a new Issuer Tenant

```json
{
  "access_token": "tenant.eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ3YWxsZXRfaWQiOiIzNTM3NmU0Yy1lYTI5LTQ1MDAtYTBhZC0xMGY3NTBkZGExM2UifQ.DEoMAD4AhLF-gHfr8JdqiRnZl31RltFIWk-al30F9Ak",
  "tenant_id": "35376e4c-ea29-4500-a0ad-10f750dda13e",
  "tenant_name": "Issuer",
  "image_url": "https://www.abc.xyz/assets/images/logo/logo.png",
  "created_at": "2022-06-07T07:53:12.584044Z",
  "updated_at": "2022-06-07T07:53:12.584044Z"
}
```

### Verifiers
Tenants are custodial wallets that are created inside the Trust Ecosystem multitenant AcaPy agent.
To create new tenants for your trust ecosystem follow the steps below:
1. Access the API through [Governance Cloud API](http://localhost:8000/docs)
2. Authenticate with `tenant-admin.`+`APIKEY` role 
3. Create a new tenant with a `POST` to the following API endpoint `/admin/tenants/` with the request body as example below
```json
{
  "image_url": "https://www.abc.xyz/assets/images/logo/logo.png",
  "name": "Verifier",
  "roles": [ "verifier"]
}
```
4. An example successful response to create a new Verifier Tenant

```json
{
  "access_token": "tenant.eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ3YWxsZXRfaWQiOiIxOTkwYzkzNS1iNTFlLTQ0NjMtODQ0Ny1hMGFmMzFlNDRlNDIifQ.SqmG9--tCLgJ1FV_31uc4yVOchX_t7oc7jHyVKq8W3w",
  "tenant_id": "1990c935-b51e-4463-8447-a0af31e44e42",
  "tenant_name": "Verifier",
  "image_url": "https://www.abc.xyz/assets/images/logo/logo.png",
  "created_at": "2022-06-07T07:56:45.045014Z",
  "updated_at": "2022-06-07T07:56:45.045014Z"
}
```
### Holders
Tenants are custodial wallets that are created inside the Trust Ecosystem multitenant AcaPy agent.
To create new tenants for your trust ecosystem follow the steps below:
1. Access the API through [Governance Cloud API](http://localhost:8000/docs)
2. Authenticate with `tenant-admin.`+`APIKEY` role 
3. Create a new tenant with a `POST` to the following API endpoint `/admin/tenants/` with the request body as example below
```json
{
  "image_url": "https://www.abc.xyz/assets/images/logo/logo.png",
  "name": "Holder"
}
```
4. An example successful response to create a new Holder Tenant

```json
{
  "access_token": "tenant.eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ3YWxsZXRfaWQiOiJjZmFmMjc2ZS1jZTc2LTQxMTYtYmUwZC03YTU0OWQ2NDgwNWIifQ.eQNCRQvKuNSlelUNZuDGpUPK7Dtvgo3uO4gDorZd2I4",
  "tenant_id": "cfaf276e-ce76-4116-be0d-7a549d64805b",
  "tenant_name": "Holder",
  "image_url": "https://www.abc.xyz/assets/images/logo/logo.png",
  "created_at": "2022-06-07T07:58:22.043147Z",
  "updated_at": "2022-06-07T07:58:22.043147Z"
}
```

## 3. Credential Definitions
Credential definitions should be written by all **_Issuers_** in the trust ecosystem who want to issue credentials to holders.  
The Trust Authority who administrates the trust ecosystem and enable tenants to write to the Indy Ledger acts as the `Transaction Endorser` of the Trust Ecosystem.  
Issuers act as `Transaction Authors` in the Trust Ecosystem.   
For more details on `Transaction Endorsers` and `Transaction Authors` please refer to [Aries Transaction Endorser Support](https://github.com/hyperledger/aries-cloudagent-python/blob/main/Endorser.md).  
To write credential definitions via the `Transaction Endorser Protocol` for trust ecosystem *issuers* follow the steps below:
1. Access the API through [Governance Cloud API](http://localhost:8000/docs)
2. Authenticate as Issuer `tenant.`+`JWTKey` role 
3. Generate a new schema with a `POST` to the following API endpoint `/generic/definitions/credentials` with the request body as example below.
> NOTE: The schema ID should already be written to the ledger and available in the Trust Registry
```json
{
  "tag": "default",
  "schema_id": "JPqFhPEM4UiR2ZNK9CM4NA:2:test_schema:0.3.0"
}
```
4. An example successful response to write a credential definition

```json
{
  "id": "EfFA6wi7fcZNWzRuHeQqaj:3:CL:8:default",
  "tag": "default",
  "schema_id": "JPqFhPEM4UiR2ZNK9CM4NA:2:test_schema:0.3.0"
}
```

## 4. Trust Registry
To query the Trust Registry entries, follow the steps below:
1. Access the API through [Governance Cloud API](http://localhost:8000/docs)
2. Authenticate as Issuer `tenant.`+`JWTKey` role 
> NOTE: The Trust Registry is currently public and accessible by anyone on the internet
3. Generate a new schema with a `GET` to the following API endpoint `/trust-registry/`.
4. An example successful response to write a credential definition

```json
{
  "actors": [
    {
      "id": "35376e4c-ea29-4500-a0ad-10f750dda13e",
      "name": "Issuer",
      "roles": [
        "issuer"
      ],
      "did": "did:sov:EfFA6wi7fcZNWzRuHeQqaj",
      "didcomm_invitation": null
    },
    {
      "id": "1990c935-b51e-4463-8447-a0af31e44e42",
      "name": "Verifier",
      "roles": [
        "verifier"
      ],
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