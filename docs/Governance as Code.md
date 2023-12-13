# Define Your Trust Ecosystem Governance

## 1. Schemas

Schemas are used to define attributes related to credentials. To define schemas for your trust ecosystem, follow the steps below:

1. Access the API through the [Governance Cloud API](http://localhost:8100/docs).
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

1. Access the API through the [Governance Cloud API](http://localhost:8100/docs).
2. Authenticate with `tenant-admin.` + `APIKEY` role.
3. Create a new tenant with a `POST` to the following API endpoint: `/admin/tenants/`, using the example request body below.

```json
{
  "wallet_label": "Demo Issuer",
  "wallet_name": "Faber",
  "roles": [
    "issuer"
  ],
  "group_id": "API demo",
  "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png"
}
```

An example of a successful response to create a new Issuer Tenant:

```json
{
  "access_token": "tenant.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ3YWxsZXRfaWQiOiIwNTYxODM2Mi1iMDI0LTQ2YzUtYjgzYy02YzZiOGM3NzkyZDgiLCJpYXQiOjE3MDAxMjgxNTN9.x_0xa9glFFW44PbfoBiEQY0Lt0dOBLVJgUkdavgusWU",
  "wallet_id": "05618362-b024-46c5-b83c-6c6b8c7792d8",
  "wallet_label": "Demo Issuer",
  "wallet_name": "Faber",
  "created_at": "2023-11-16T09:49:13.067595Z",
  "updated_at": "2023-11-16T09:49:13.111843Z",
  "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
  "group_id": "API demo"
}
```

### Verifiers

Tenants, functioning as custodial wallets, are established within the Trust Ecosystem's multitenant AcaPy agent. Follow the steps below to create new tenants for your trust ecosystem:

1. Access the API through [Governance Cloud API](http://localhost:8100/docs)
2. Authenticate using the `tenant-admin.`+`APIKEY` role
3. Generate a new tenant with a `POST` request to the API endpoint `/admin/tenants/` using the request body detailed in the example below

   ```json
   {
    "wallet_label": "Demo Verifier",
    "wallet_name": "Acme",
    "roles": [
     "verifier"
    ],
    "group_id": "API demo",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png"
   }'
   ```

4. Below is an example of a successful response to the creation of a new Verifier Tenant:

   ```json
   {
    "access_token": "tenant.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ3YWxsZXRfaWQiOiIwNTYxODM2Mi1iMDI0LTQ2YzUtYjgzYy02YzZiOGM3NzkyZDgiLCJpYXQiOjE3MDAxMjgxNTN9.x_0xa9glFFW44PbfoBiEQY0Lt0dOBLVJgUkdavgusWU",
    "wallet_id": "05618362-b024-46c5-b83c-6c6b8c7792d8",
    "wallet_label": "Demo Verifier",
    "wallet_name": "Acme",
    "created_at": "2023-11-16T09:49:13.067595Z",
    "updated_at": "2023-11-16T09:49:13.111843Z",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
    "group_id": "API demo"
   }
   ```

### Holders

Similar to Verifiers, Tenants for Holders are created within the Trust Ecosystem's multitenant AcaPy agent. Follow these steps to create new Holders for your trust ecosystem:

1. Access the API through [Governance Cloud API](http://localhost:8100/docs)
2. Authenticate using `tenant-admin.`+`APIKEY` role
3. Generate a new tenant with a `POST` to the API endpoint `/admin/tenants/` using the request body in the example below

   ```json
   {
    "wallet_label": "Demo Holder",
    "wallet_name": "Alice",
    "group_id": "API demo",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png"
   }
   ```

4. Here is an example of a successful response to creating a new Holder Tenant:

   ```json
   {
    "access_token": "tenant.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ3YWxsZXRfaWQiOiI0ZTBjNzBmYi1mMmFkLTRmNTktODFmMy05M2Q4ZGY5Yjk3N2EiLCJpYXQiOjE3MDAxMTkzMjJ9.lXrNVWN_bzRXkkBfOd1Yey6D0iqsHpOuXt6aZYwMLp4",
    "wallet_id": "4e0c70fb-f2ad-4f59-81f3-93d8df9b977a",
    "wallet_label": "Demo Holder",
    "wallet_name": "Alice",
    "created_at": "2023-11-16T07:22:02.086605Z",
    "updated_at": "2023-11-16T07:22:02.105980Z",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
    "group_id": "API demo"
   }
   ```

## 3. Credential Definitions

Credential definitions are expected to be created by all **_Issuers_** within the trust ecosystem who wish to issue credentials to holders. The Trust Authority, which administers the trust ecosystem and enables tenants to write to the Indy Ledger, acts as the `Transaction Endorser` of the Trust Ecosystem. Meanwhile, Issuers serve as `Transaction Authors` within the Trust Ecosystem. For additional information on `Transaction Endorsers` and `Transaction Authors`, please refer to [Aries Transaction Endorser Support](https://github.com/hyperledger/aries-cloudagent-python/blob/main/Endorser.md).

To create credential definitions through the `Transaction Endorser Protocol` for trust ecosystem _issuers_, follow the steps below:

1. Access the API through [Governance Cloud API](http://localhost:8100/docs)
2. Authenticate as an Issuer using `tenant.`+`JWTKey` role
3. Create a new schema with a `POST` to the API endpoint `/generic/definitions/credentials` using the request body illustrated in the example below.

   >NOTE: The schema ID should already exist in the ledger and be accessible in the Trust Registry

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

1. Access the API through [Governance Cloud API](http://localhost:8100/docs)
2. Authenticate as an Issuer using `tenant.`+`JWTKey` role

   >NOTE: The Trust Registry is currently public and accessible to anyone on the internet

3. The trust-registry has 5 GET endpoints:
   - `GET`  `/trust-registry/schemas`
     - Will return all schemas on the trust registry

     Response

    ```json
    [
      {
        "did": "GXK1Ubc58DvZDe48zPYdcf",
        "name": "Proof of Person",
        "version": "0.1.0",
        "id": "GXK1Ubc58DvZDe48zPYdcf:2:Proof of Person:0.1.0"
      },
      {
        "did": "GXK1Ubc58DvZDe48zPYdcf",
        "name": "Proof of Address",
        "version": "0.1.0",
        "id": "GXK1Ubc58DvZDe48zPYdcf:2:Proof of Address:0.1.0"
      },
      {
        "did": "GXK1Ubc58DvZDe48zPYdcf",
        "name": "Proof of Medical Aid",
        "version": "0.1.0",
        "id": "GXK1Ubc58DvZDe48zPYdcf:2:Proof of Medical Aid:0.1.0"
      },
      {
        "did": "GXK1Ubc58DvZDe48zPYdcf",
        "name": "Proof of Bank Account",
        "version": "0.1.0",
        "id": "GXK1Ubc58DvZDe48zPYdcf:2:Proof of Bank Account:0.1.0"
      }
    ]
    ```

   - `Get` `/trust-registry/schemas/{schema_id}`
     - Will return the schema based on id passed

     Response

    ```json
    {
      "did": "GXK1Ubc58DvZDe48zPYdcf",
      "name": "Proof of Bank Account",
      "version": "0.1.0",
      "id": "GXK1Ubc58DvZDe48zPYdcf:2:Proof of Bank Account:0.1.0"
    }
    ```

    - `GET` `/trust-registry/actors`
      - Will return all actors on the trust registry
      - Optionally one of the following query parameters can be passed to get a specific actor:
        >NOTE: Only one of these can be passed at any time
        - `actor_did`
        - `actor_id`
        - `actor_name`

     Response

    ```json
    [
      {
        "id": "9bdbc626-1499-48e2-a5db-878d347e290b",
        "name": "didxissuer@didx.co.za",
        "roles": [
          "issuer"
        ],
        "did": "did:sov:J1Sg8UHXyuyBCUUpRY3EeZ",
        "didcomm_invitation": "http://localhost:8100?oob=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL291dC1...Y29tbS5vcmcvZGlkZXhjaGFuZ2UvMS4wIl19"
      },
      {
        "id": "fe523496-e0b5-4aea-a038-6ed6cbd686b8",
        "name": "didxverifier@didx.co.za",
        "roles": [
          "verifier"
        ],
        "did": "did:key:z6MkkUK3zRys1WezsaoAtXZtAJrhP7dh5qxbpJMe6cbDcW3s",
        "didcomm_invitation": "http://localhost:8100?oob=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL291dC1vZi1iYW...jb21tLm9yZy9kaWRleGNoYW5nZS8xLjAiXX0="
      },
      {
        "id": "cf058a03-1f88-4fa9-97dc-96a9cabf8d3e",
        "name": "Bank Issuer & Verifier",
        "roles": [
          "issuer",
          "verifier"
        ],
        "did": "did:sov:UhJ5C8hgSiNzpoAYwVcnW9",
        "didcomm_invitation": "http://localhost:8100?oob=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3Jn...odHRovL2RpZGNvbW0ub3JnL2RpZGV4Y2hhbmdlLzEuMCJdfQ=="
      }
    ]
    ```

   - `GET` `/trust-registry/actors/issuers`
     - Will return all actors with `issuer` as a role

     Response

    ```json
    [
      {
        "id": "9bdbc626-1499-48e2-a5db-878d347e290b",
        "name": "didxissuer@didx.co.za",
        "roles": [
          "issuer"
        ],
        "did": "did:sov:J1Sg8UHXyuyBCUUpRY3EeZ",
        "didcomm_invitation": "http://localhost:8100?oob=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL291dC1vZ...hjaGFuZ2UvMS4wIl19"
      },
      {
        "id": "cf058a03-1f88-4fa9-97dc-96a9cabf8d3e",
        "name": "Bank Issuer & Verifier",
        "roles": [
          "issuer",
          "verifier"
        ],
        "did": "did:sov:UhJ5C8hgSiNzpoAYwVcnW9",
        "didcomm_invitation": "http://localhost:8100?oob=eyJAdHlwZSI6ICJo2RpZGNvbW0ub3JnL291dC1vZi1iYW5zIjogWyJodHRwc...ovL2RpZGNvbW0ub3JnL2RpZGV4Y2hhbmdlLzEuMCJdfQ=="
      }
    ]
    ```

    - `GET` `/trust-registry/actors/verifiers`
      - Will return all actors with `verifier` as a role

     Response

    ```json
    [
      {
        "id": "fe523496-e0b5-4aea-a038-6ed6cbd686b8",
        "name": "didxverifier@didx.co.za",
        "roles": [
          "verifier"
        ],
        "did": "did:key:z6MkkUK3zRys1WezsaoAtXZtAJrhP7dh5qxbpJMe6cbDcW3s",
        "didcomm_invitation": "http://localhost:8100?oob=eyJAdHlwZSI6ICJodHRwczovL2RpZGNvbW0ub3JnL291dC1vZi1iYW5kLzEuMS9...9yZy9kaWRleGNoYW5nZS8xLjAiXX0="
      },
      {
        "id": "cf058a03-1f88-4fa9-97dc-96a9cabf8d3e",
        "name": "Bank Issuer & Verifier",
        "roles": [
          "issuer",
          "verifier"
        ],
        "did": "did:sov:UhJ5C8hgSiNzpoAYwVcnW9",
        "didcomm_invitation": "http://localhost:8100?oob=eyJAdHlwZSI6ICJodHbW0ub3JnL291dC1vZi1iYWyJodHRwcz...ovL2RpZGNvbW0ub3JnL2RpZGV4Y2hhbmdlLzEuMCJdfQ=="
      }
    ]
    ```
