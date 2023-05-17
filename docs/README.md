# Introduction to Aries Cloud API

## Trust Ecosystem in a Box

## Table of Contents

1. [First Step and Overview](#first-steps)
2. [Cloud API Roles](#cloudapi-roles)
3. [Workflows and Roles Overview](#workflows-and-roles-overview)
4. [Workflows Overview](Workflows%20Overview.md)
5. [Bootstrap a Trust Ecosystem using Aries Cloud API](./Bootstrap%20Trust%20Ecosystem.md)
6. [Governance as Code](./Governance%20as%20Code.md)
7. [Common Steps](./Common%20Steps.md)
8. [Webhooks](Webhooks.md)
9. [Trust Registry](Trust%20Registry.md)
10. [Aries Cloud API Architecture Overview](Aries%20Cloud%20API%20Architecture.md)
11. [Quick Start Guide](Quick%20Start%20Guide.md)

## First Steps

After spinning up the containers following the [Quick Start Guide](Quick%20Start%20Guide.md), you are ready to rumble. Navigating to the [swagger UI](http://localhost:8000/docs/) provides a good overview of the intended functionalities.

You'll see that there are `generic` endpoints for common actions, wallet specific actions, and admin actions. On top of that, you'll find the trust registry and webhooks being exposed. These are the intended ways of client interactions with these two services.

NOTE: Regardless of the multitude of containers and mechanisms running, [The CloudAPI](http://localhost:8000) and its [SwaggerUI](http://localhost:8000/docs) are the main interaction points intended between clients and the stack. This should be the only endpoint clients should (have to) interact with. There is no need (and no intention to allow that) for clients to directly interact with the webhooks or trust registry container. For a production deployment or a close-to-production/smoke-testing deployment, you are well advised to only expose this endpoint to clients and leave all other endpoints unexposed to the outside world.

### Using the Swagger UI

The Swagger UI is documented. It shows you endpoints, expected parameters, and what example requests and responses look like. At the bottom of the UI, you can also find a list of all types used that includes definition and example values.

### Following Docker Container Logs

It can be handy to follow the logs of a specific container. A convenient way to do so is using:

```bash
docker logs --follow $(docker ps -f name="YOUR_CONTAINER_NAME" | awk 'FNR == 2 {print $1}')
```

And replacing `YOUR_CONTAINER_NAME` with the name of the container you want to follow (e.g., governance-webhooks-web). You can find the container name in the docker-compose.yaml.

### Authentication

Authentication is handled by the CloudAPI and, from a client perspective, kept simple and convenient. Either, via the Swagger UI auth (padlock button in UI) or via the HEADER data of your client specifying an `x-api-key`. Regardless of whether you use the UI or another client, the `x-api-key` value consists of two parts, separated by a dot:

`{role}.{key/token}`

So, your header has the format `'x-api-key: {role}.{key/token}` which yields, for example, `'x-api-key: governance.adminApiKey'`

The first part `role` specifies the role on the surface and targets the correct endpoints under the hood and authentication mechanisms under the hood. The CloudAPI knows how to interpret the roles and will produce the correct target URLs for e.g., ACA-Py (`tenant` targets the multitenant agent) with the correct header expected by the ACA-Py agent. For instance, `tenant` results in a `Bearer {TOKEN}` header against the multitenant agent whereas `tenant-admin` as role results in an `x-api-key` header for the multitenant agent (hence targeting the admin interface of the same multitenant agent). You may have noticed now that this mechanism also chooses which ACA-Py instance to target without having to know or specify the URL the agent resides under.

The `governance` and `-admin` suffixed roles are admin roles. The rest are non-admin roles meaning non-admin roles have no exposure to the ACA-Py admin tasks nor any documented endpoints prefixed `admin:` in the CloudAPI.

For admin roles pass the admin password as the second part of `{role}.{key/token}`. For tenant (non-admin role) pass the wallets JWT as the second part of `{role}.{key/token}`.

Currently, there are three options for `role`:

### CloudAPI Roles

#### Governance Role

Authentication header example `'x-api-key: governance.adminApiKey'`

- governance
  - is:
    - trust authority
    - transaction endorser
  - can:
    - make connections
    - create schemas
    - create credential definitions
    - manage trust registry
    - issue credential
    - verify credential
    - send basic messages

#### Tenant Administration Role

Authentication header example `'x-api-key: tenant-admin.adminApiKey'`

- tenant-admin
  - is:
    - trust ecosystem admin
    - is transaction author
  - can:
    - only create, update, and delete tenants (_wallets_) for trust ecosystem issuers, verifiers, and users

#### Tenant Role (Trust Ecosystem Issuers, Verifiers, and Holders)

Authentication header example `'x-api-key: tenant.eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ3YWxsZXRfaWQiOiIxZGZlOTFlNy0yNTE0LTRmYzMtODg0ZC1kYTQwOWJlODcwODMifQ.qLstLxdbnfwFSZjBNJX3GXko-ZYTMVOpOZWgmfJ1x3g'`

- tenant
  - is:
    - holder
    - issuer/verifier
  - if is issuer or verifier
    - issuers are transaction authors
    - verifiers are not transaction authors
    - automatically registered with the trust registry
    - can:
      - make connections
      - create credential definitions
      - issue credential
      - create/manage wallets
      - all transactions written to the ledger are counter-signed by the governance transaction endorser role
  - if is user (_holder_):
    - holder only
    - can:
      - make connections
      - manage own wallet (holder)
      - receive and store credentials
      - respond to/create proof request
      - messaging, etc.

### Workflows and Roles Overview

#### Creating schemas

Using the admin role(s) you can create and register schemas. Successful schema creation will automatically write it to the ledger.

The ledger is also a useful place to look at what schemas you have at your disposal. In fact, this should be the preferred way because schemas can exist on the ledger but have been invalidated on the trust registry. This will be checked by the CloudAPI and only valid schemas are allowed foruse.

#### Credentials

The main feature evolves around issuing credentials and proofs based on these credentials.

#### Creating and issuing credentials

In order to issue a credential one must first:

- Create a schema and
- Register the schema with the trust registry.

via the governance agent.

Then:

- Register an issuer (on the trust registry) via the governance agent

The registered issuer can now issue a credential and related schema on the trust registry.

Now:

- Create a connection between the issuer and some other entity that you want to hold a credential
- Using the connection ID, create and issue a credential (have a look at the models in Swagger - it will tell you what data you need to provide and will receive back)
- Holder accepts credential issuance
- Holder stores credential in wallet

Hooray 🥳 🎉. What has happened? We have:

- Created a schema (using the governance admin)
- Registered a schema on the ledger (via the governance admin)
- Created (a wallet for) an issuer and future holder using the admin agent
- Registered an issuer (for a schema)
- Created a connection between an issuer and a prospective holder (using connections/invitations API)
- Proposed a credential to a prospective holder from an issuer
- Accepted and stored an offered credential

Please note that when creating/issuing a credential, endorsing, and verifying credentials, the CloudAPI checks whether the requested instructions are valid against the trust registry.

#### Requesting a proof/using a credential

Now that we have an entity holding a credential (having a stored credential in their wallet), the next step is to use this credential. What we need to do:

- Register a verifier on the trust registry (using the admin agent).
- Establish a connection between a holder (of a credential) and a verifier (using connections/invitations API).
- Using the data models and the ['dance' described in the ACA-Py docs](https://github.com/hyperledger/aries-rfcs/tree/main/features/0037-present-proof), you can now arrange for negotiating a proof exchange

#### User management/Creating wallets

Using the admin role(s), you can create wallets for tenant or eco-system partners. These are all sub wallets. Successful creation returns the wallet creation response, including the wallet id and JWT for authentication.
