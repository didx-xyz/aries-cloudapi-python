# Workflows Overview

## First Steps

After spinning up the containers following the [Quick Start Guide](./Quick%20Start%20Guide.md), you are ready to rumble. Navigating to the [Swagger UI](http://localhost:8000/docs/) provides a good overview of the intended functionalities.

You'll see that there are `generic` endpoints for common actions, wallet-specific actions, and admin actions. Additionally, you'll find the trust registry and webhooks being exposed. These are the intended ways of client interactions with these two services.

> NOTE: Regardless of the multitude of containers and mechanisms running, [The CloudAPI](http://localhost:8000) and its [SwaggerUI](http://localhost:8000/docs) are the main interaction points intended between clients and the stack. This should be the only endpoint clients should (and have to) interact with. There is no need (and no intention to allow that) for clients to directly interact with the webhooks or trust registry container. For a production deployment or a close-to-production/smoke-testing deployment, you are well advised to only expose this endpoint to clients and leave all other endpoints unexposed to the outside world.

### Trust Registry

As a client, you can retrieve the trust registry (and NOT alter it). That is intentional and all a consumer/client should and is able to do. Altering the trust registry is baked into admin actions and only possible with an admin role.

> NOTE: The Trust Registry GET API endpoint is not protected.

### Webhooks

A client can subscribe to the webhooks via the CloudAPI (as opposed to directly via the webhooks container). This requires only targeting the `/webhooks` endpoint and optionally targeting the `/webhooks/{topic}` sub-route by suffixing a topic. Using the auth mechanism (see section below), the app automatically extracts the required info about the wallet (i.e., the wallet id and JWT) and retrieves only the associated webhooks with a particular wallet. Failing to authenticate will return a 403 HTTP Error.

#### Rolling Your Webhook Listener

You can (given you are within the Docker network) use a pubsub client (see also `webhooks/clients.example.py`):

```python
from fastapi_websocket_pubsub import PubSubClient
import asyncio

async def on_events(data, topic):
    print(f"{topic}:\n{data}")

async def main():
    # Create a client and subscribe to topics
    topics = [
        "connections",
        "credentials",
        "proofs",
        "endorsements",
        "basic-messages"
    ]
    client = PubSubClient([*topics], callback=on_events)

    client.start_client(f"ws://127.0.0.1:3010/pubsub")
    await client.wait_until_done()

asyncio.run(main())
```

## Authentication

Authentication is handled by the CloudAPI and, from a client perspective, kept simple and convenient. Either via the Swagger UI auth (padlock button in UI) or via the HEADER data of your client specifying an `x-api-key`. Regardless of whether you use the UI or another client, the `x-api-key` value consists of two parts, separated by a dot:

`{role}.{key/token}`

So, your header has the format `x-api-key: {role}.{key/token}` which yields, for example, `x-api-key: governance.adminApiKey`.

The first part `role` specifies the role on the surface and targets the correct endpoints and authentication mechanisms under the hood. The CloudAPI knows how to interpret the roles and will produce the correct target URLs for e.g., ACA-Py (`tenant` targets the multitenant agent) with the correct header expected by the ACA-Py agent. For instance, `tenant` results in a `Bearer {TOKEN}` header against the multitenant agent, whereas `tenant-admin` as a role results in an `x-api-key` header for the multitenant agent (hence targeting the admin interface of the same multitenant agent). You may have noticed now that this mechanism also chooses which ACA-Py instance to target without having to know or specify the URL the agent resides under.

Currently, there are three options for `role`:

## CloudAPI Roles

### Governance Role

- governance
  - is:
    - trust authority
    - transaction endorser
  - can:
    - make connections
    - create schemas
    - create credential definitions
    - manage trust registry
    - issue credentials
    - verify credentials
    - send basic messages

### Tenant Administration Role

- tenant-admin
  - is:
    - trust ecosystem admin
    - transaction author
  - can:
    - only create, update, and delete tenants (_wallets_) for trust ecosystem issuers, verifiers, and users

### Tenant Role (Trust Ecosystem Issuers, Verifiers, and Holders)

- tenant
  - is:
    - holder
    - issuer/verifier
  - if is issuer or verifier:
    - issuers are transaction authors
    - verifiers are not transaction authors
    - automatically registered with the trust registry
    - can:
      - make connections
      - create credential definitions
      - issue credentials
      - create/manage wallets
      - all transactions written to the ledger are counter-signed by the governance transaction endorser role
  - if is user (_holder_):
    - holder only
    - can:
      - make connections
      - manage own wallet (holder)
      - receive and store credentials
      - respond to/create proof request
      - messaging, etc. ...

The `governance` and `-admin` suffixed roles are admin roles. The rest are non-admin roles, meaning non-admin roles have no exposure to the ACA-Py admin tasks nor any documented endpoints prefixed `admin:` in the CloudAPI.

For admin roles, pass the admin password as the second part of `{role}.{key/token}`. For tenant (non-admin role), pass the wallet's JWT as the second part of `{role}.{key/token}`.

## Creating Schemas

Using the admin role(s), you can create and register schemas. Successful schema creation will automatically write it to the ledger.

The ledger is also a useful place to look at what schemas you have at your disposal. In fact, this should be the preferred way because schemas can exist on the ledger but have been invalidated on the trust registry. This will be checked by the CloudAPI and only valid schemas are allowed for use.

## Credentials

(One of) the main feature(s) revolves around issuing credentials and proofs based on these credentials.

### Creating and Issuing Credentials

In order to issue a credential, one must first:

- create a schema and
- register the schema with the trust registry

via the governance agent.

Then:

- Register an issuer (on the trust registry) via the governance agent.

The registered issuer can now issue a credential related to a schema on the trust registry.

Now:

- Create a connection between the issuer and some other entity that you want to hold a credential
- Using the connection ID, create and issue a credential (have a look at the models in Swagger - it will tell you what data you need to provide and will receive back)
- The holder accepts credential issuance
- The holder stores the credential in their wallet

Hooray🥳 🎉. What has happened? We have:

- Created a schema (using the governance admin)
- Registered a schema on the ledger (via the governance admin)
- Created (a wallet for) an issuer and future holder using the admin agent
- Registered an issuer (for a schema)
- Created a connection between an issuer and a prospective holder (using connections/invitations API)
- Proposed a credential to a prospective holder from an issuer
- Accepted and stored an offered credential

Please note that when creating/issuing a credential, endorsing, and verifying credentials, the CloudAPI checks whether the requested instructions are valid against the trust registry.

### Requesting a Proof/Using a Credential

Now that we have an entity holding a credential (having a stored credential in their wallet), the next step is to use this credential. What we need to do:

- Register a verifier on the trust registry (using the admin agent).
- Establish a connection between a holder (of a credential) and a verifier (using connections/invitations API).
- Using the data models and the ["dance" described in the ACA-Py docs](https://github.com/hyperledger/aries-rfcs/tree/main/features/0037-present-proof), you can now arrange for negotiating a proof exchange.

## User Management/Creating Wallets

Using the admin role(s), you can create wallets for tenants or ecosystem partners. These are all sub-wallets. Successful creation returns the wallet creation response, including the wallet id and JWT for authentication.

## Using the Swagger UI

The Swagger UI is documented. It shows you endpoints, expected parameters, and what example requests and responses look like. At the bottom of the UI, you can also find a list of all types used that includes definition and example values.

## Following Logs

It can be handy to follow the logs of a specific container. A convenient way to do so is using:

```bash
docker logs --follow $(docker ps -f name="YOUR_CONTAINER_NAME" | awk 'FNR == 2 {print $1}')
```

and replacing `YOUR_CONTAINER_NAME` with the name of the container you want to follow (e.g., governance-webhooks-web). You can find the container name in the docker-compose.yaml.
