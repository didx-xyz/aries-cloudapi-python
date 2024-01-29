# Introduction to Aries Cloud API

## Trust Ecosystem in a Box

## Table of Contents

1. [First Step and Overview](#first-steps)
2. [Cloud API Roles](#cloudapi-roles)
3. [Workflows and Roles Overview](#workflows-and-roles-overview)
4. [Further Reading](#further-reading)

## First Steps

After spinning up the containers following the [Quick Start Guide](Quick%20Start%20Guide.md), you are ready to rumble. Navigating to the [Swagger UI](http://localhost:8100/docs/) provides a good overview of the intended functionalities. You'll see that there are `generic` endpoints for common actions, wallet specific actions, and admin actions. On top of that, you'll find trust registry and webhooks endpoints.

>NOTE: Regardless of the multitude of containers and mechanisms running, [CloudAPI](http://localhost:8100) and its [Swagger UI](http://localhost:8100/docs) are the main interaction points intended between clients and the stack. This should be the only endpoint clients should interact with. There is no need (and no intention to allow) for clients to directly interact with the webhooks or trust registry container. For a production deployment or a close-to-production/smoke-testing deployment, you are well advised to only expose this endpoint to clients and leave all other endpoints unexposed to the outside world.

### Using the Swagger UI

The Swagger UI is documented. It shows you endpoints, expected parameters, and what example requests and responses look like. At the bottom of the UI, you can also find a list of all request/response models used, with definitions and example values.

### Following Docker Container Logs

It can be handy to follow the logs of a specific container. A convenient way to do so is using:

```bash
docker logs --follow $(docker ps -f name="YOUR_CONTAINER_NAME" | awk 'FNR == 2 {print $1}')
```

And replacing `YOUR_CONTAINER_NAME` with the name of the container you want to follow (e.g., governance-webhooks-web). You can find the container name in the docker-compose.yaml.

### Authentication

Authentication is handled by the CloudAPI, and from a client perspective it's kept simple and convenient. Either, via the Swagger UI auth (padlock button in UI) or via the header data of your client specifying an `x-api-key`. Regardless of whether you use the UI or another client, the `x-api-key` value consists of two parts, separated by a dot:

`{role}.{key/token}`

This means the header has the format `'x-api-key: {role}.{key/token}`, which would look like, e.g., `'x-api-key: governance.adminApiKey'` or `'x-api-key: tenant.ey..'` (JWT token).

The first part, `role`, specifies the role on the surface and targets the correct endpoints and authentication mechanisms under the hood. CloudAPI knows how to interpret the roles and will produce the correct target URLs for the ACA-Py agent (`tenant` and `tenant-admin` target the multitenant agent, and `governance` targets the governance agent) with the correct headers expected by the agent.

For admin roles, pass the agent API key as the second part of `{role}.{key}`:

- The `governance` role requires the Governance Agent API Key (which was used in starting up the governance agent) as the right-hand side token in the `x-api-key` header (in order to authenticate access to the governance agent).
- The `tenant-admin` role requires the Multitenant Agent API Key (which was used in starting up the multitenant agent) as the right-hand side token in the `x-api-key` header (in order to target the admin interface of the multitenant agent).

Requests for the `tenant` role require the wallet JWT as the token in `{role}.{token}`. These requests will internally obtain a `Bearer {TOKEN}` header passed to the multitenant agent.

The definitions and capabilities of the three roles are as follows:

### CloudAPI Roles

#### Governance Role

Authentication header: `'x-api-key: governance.<GOVERNANCE AGENT API KEY>'`

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

Authentication header: `'x-api-key: tenant-admin.<MULTITENANT AGENT API KEY>'`

- tenant-admin
  - is:
    - trust ecosystem admin
    - is transaction author
  - can:
    - only create, update, and delete tenants (_wallets_) for trust ecosystem issuers, verifiers, and users

#### Tenant Role (Trust Ecosystem Issuers, Verifiers, and Holders)

Authentication header: `'x-api-key: tenant.<TENANT JWT>'`

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
      - send basic messages

### Workflows and Roles Overview

#### Creating schemas

Using the admin role(s) you can create and register schemas. Successful schema creation will automatically write it to the ledger.

The ledger is also a useful place to look at what schemas you have at your disposal. In fact, this should be the preferred way, because schemas can exist on the ledger but have been invalidated on the trust registry. This will be checked by the CloudAPI and only valid schemas are allowed for use.

#### Credentials

The main feature revolves around issuing credentials, and verifying proofs based on these credentials.

#### Creating and issuing credentials

In order to issue a credential one must first:

- Create a schema and
- Register the schema with the trust registry.

via the governance agent.

Then:

- Register an issuer (on the trust registry) with a tenant admin controller.

The registered issuer can then issue a credential and related schema on the trust registry with the following steps:

- Create a connection between the issuer and some other entity that you want to hold a credential
- Once a connection is established, use the connection ID to create and issue a credential (have a look at the models in Swagger - it will tell you what data you need to provide and will receive back)
- Holder accepts credential issuance
- Holder stores credential in wallet

In summary, we have:

- Created a schema (using the governance admin)
- Registered a schema on the ledger (via the governance admin)
- Created (a wallet for) an issuer and future holder using the tenant-admin
- Registered an issuer (for a schema)
- Created a connection between an issuer and a prospective holder (using connections API)
- Proposed a credential to a prospective holder from an issuer
- Accepted and stored an offered credential

Please note that when creating/issuing a credential, endorsing, and verifying credentials, the CloudAPI checks whether the requested instructions are valid against the trust registry.

#### Requesting a proof/using a credential

Now that we have an entity holding a credential (having a stored credential in their wallet), the next step is to use this credential. What we need to do:

- Register a verifier on the trust registry (using a tenant-admin controller).
- Establish a connection between a holder (of a credential) and a verifier (using connections/invitations API).
- Using the data models and the ['dance' described in the ACA-Py docs](https://github.com/hyperledger/aries-rfcs/tree/main/features/0037-present-proof), you can now arrange for negotiating a proof exchange

#### User management/Creating wallets

Using the admin role(s), you can create wallets for tenant or eco-system partners. These are all sub wallets. Successful creation returns the wallet creation response, including the wallet id and JWT for authentication.

## Further Reading

- [Aries Cloud API Architecture Overview](Aries%20Cloud%20API%20Architecture.md)
- [Quick Start Guide](Quick%20Start%20Guide.md)
- [Bootstrap the Trust Ecosystem](./Bootstrap%20Trust%20Ecosystem.md)
- [Common Steps](./Common%20Steps.md)
- [Example Flows](./Example%20Flows.md)
- [Governance as Code](./Governance%20as%20Code.md)
- [Trust Registry](Trust%20Registry.md)
- [Webhooks](./Webhooks.md)
