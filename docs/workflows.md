## Workflows

### First Steps

After spinning up the containers following the `README` or `intro.md` you are ready ot rumble. Navigating to the [swagger UI](http://localhost:8000/docs/) provides a good overview of the intended functionalities.

You see that there are `generic` endpoints for common actions, wallet specific actions and admin actions. On top of that, you find th trust registry and webhooks being exposed. These are the intended ways of client interactions with these two services.

NOTE: Regardless of the multitude of containers and mechanisms running, [the CloudAPI](http://localhost:8000) and its [SwaggerUI](http://localhost:8000/docs) are the main interaction point intended between clients and the stack. This should be the only endpoint clients should (have to) interact with. There is no need (and no intention to allow that) for client to directly interact with the webhooks or trust registry container. For a production deployment or a close-to-production/smoke-testing deployment, you are well advised to only expose this endpoint to clients and leave all other endpoints unexposed to the outside world.

#### Trust registry

As a client you can retrieve the trust registry (and NOT alter it). That is intentional and all a consumer/client should and is able to do. Altering the trust registry is baked into admin actions and only possible with admin role.

#### Webhooks

A client can subscribe to the webhooks via the CloudAPI (as opposed to directly via the webhooks container). This requires only targeting the `/webhooks` endpoint and optionally targeting the `/webhooks/{topic}` sub-route by suffixing a topic. Using the auth mechanism (see section below), the app automatically extracts the required info about the wallet (i.e the wallet id and JWT) and retrieves only the associated webhooks with a particular wallet. Failing to authenticate will return a 403 HTTP Error.

##### Rolling your webhook listener

You can either implement a polling mechanism. Here is an example in python (see also `app/tests/util/webhooks.py`):

```python
# For a wallet poll the webhooks until a state is satisfied - fail otherwise
def check_webhook_state(
    client: AsyncClient,
    topic: topics,
    filter_map: Dict[str, Optional[str]] = {},
    max_duration: int = 15,
    poll_interval: int = 1,
) -> bool:
    assert poll_interval >= 0, "Poll interval cannot be negative"
    assert max_duration >= 0, "Poll duration cannot be negative"

    wallet_id = get_wallet_id_from_async_client(client)

    t_end = time.time() + max_duration
    while time.time() < t_end:
        hooks = httpx.get(f"{WEBHOOKS_URL}/{topic}/{wallet_id}").json()

        # Loop through all hooks
        for hook in hooks:
            payload = hook["payload"]
            # Find the right hook
            match = all(
                payload.get(filter_key, None) == filter_value
                for filter_key, filter_value in filter_map.items()
            )

            if match:
                return True

        time.sleep(poll_interval)
    raise Exception(f"Cannot satisfy webhook filter \n{filter_map}\n. Found \n{hooks}")


## Retrieve webhooks per topic
def get_hooks_per_topic_per_wallet(client: AsyncClient, topic: topics) -> List:
    wallet_id = get_wallet_id_from_async_client(client)
    try:
        hooks = (httpx.get(f"{WEBHOOKS_URL}/{topic}/{wallet_id}")).json()
        return hooks if hooks else []
    except httpx.HTTPError as e:
        raise e from e
```

or you can (given you are within the docker-compose network or have expose the websockets - which you should NOT do) use a pubsub client (see also `webhooks/clients.example.py`):

```python
# Example ws client connecting to all topics for acapy
from fastapi_websocket_pubsub import PubSubClient
import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.basename(__file__), "..")))

PORT = os.getenv("PORT", "3010")
URL = os.getenv("WEBHOOKS_URL", "127.0.0.1")


async def on_events(data, topic):
    print(f"{topic}:\n{data}")


async def main():
    # Create a client and subscribe to topics
    topics = [
        "connections",
        "issue_credential",
        "forward",
        "ping",
        "basicmessages",
        "issuer_cred_rev",
        "issue_credential_v2_0",
        "issue_credential_v2_0_indy",
        "issue_credential_v2_0_dif",
        "present_proof",
        "present_proof_v2",
        "revocation_registry",
    ]
    client = PubSubClient([*topics], callback=on_events)

    """
    # You can also register it using the commented code below
    async def on_data(data, topic):
        print(f"{topic}:\n", data)

    [client.subscribe(topic, on_data) for topic in topics]
    """

    client.start_client(f"ws://{URL}:{3010}/pubsub")
    await client.wait_until_done()


asyncio.run(main())
```

### Authentication

Authentication is handled by the CloudAPI and, fom a client perspective, kept simple and convenient. Either, via the Swagger UI auth (padlock button in UI) or via the HEADER data of your client specifying an `x-api-key`. Regardless of whether ou use the UI or another client, the `x-api-key` value consists of two parts, separated by a dot:

`{role}.{key/token}`

So, your header has the format `'x-api-key: {role}.{key/token}` which yields, for example, `'x-api-key: yoma.adminApiKey'`

The first part `role` specifies the role on the surface and targets the correct endpoints under the hood and authentication mechanisms under the hood. The CloudAPI knows how to interpret the roles and will produce the correct target URLs for eg aca-py (`member` targets the multitenant agent) with the correct header expected by aca-py agent. For instance, `member` results in a `Bearer {TOKEN}` header against the multitenant agent whereas `member-admin` as role results in an `x-api-key` header for the multitenant agent (hence targeting the admin interface of the same multitenant agent). You may have noticed now that this mechanism also chooses which aca-py instance to target without having to know or specify the URL the agent resides under.

Currently there are five options for `role`:

- yoma
  - is:
    - endorser
  - can:
    - create schemas
    - manage trust registry
    - create/ manage wallets
    - issue credential
- ecosystem
  - is:
    - holder
    - issuer/verifier
    - automatically registered with the trust registry
  - can:
    - create schemas/ issue credential
    - create/manage wallets
    - issue credential
- ecosystem-admin
  - is:
    - ecosystem admin
  - can:
    - only create new tenants/wallets for ecosystem
- member
  - is:
    - member instance
    - holder only
  - can:
    - manage own wallet (holder)
    - receive and store credentials
    - respond to/create proof request
    - messaging etc. ...
- member-admin
  - is:
    - member admin
  - can:
    - only create new tenants/wallets for members

the `yoma` and `-admin` suffixed roles are admin roles. The rest are non-admin roles meaning non-admin roles have no exposure to the aca-py admin tasks nor any documented endpoints prefixed `admin:` in the CloudAPI.

For admin roles pass the admin password as the second part of `{role}.{key/token}`. For member/ecosystem (non-admin roles) pass the wallets JWT as the second part of `{role}.{key/token}`.

### Creating schemas

Using the admin role(s) you can create and register schemas. Successful schema creating will automatically write it to the ledger.

The ledger is also a useful place to look at what schemas you have at your disposal. In fact, this should be the preferred way because schemas can exist on the ledger but have been invalidated on the trust registry. This will be checked by the CloudAPI and only valid schemas are allowed for use.

### User management/Creating wallets

Using the admin role(s) you can create wallets for tenant or eco-system partners. These are all sub wallets. Successful creation return the wallet creation response including the wallet id and JWT for authentication.

### Using the swagger UI

The Swagger UI is documented. It shows you endpoints, expected parameters and what example requests and responses look like. At the bottom of the UI you can also find a list of all types used that includes definition and example values.

### Following logs

It can be handy to follow the logs of a specific container. A convenient way to do so is using:

```bash
docker logs --follow $(docker ps -f name="YOUR_CONTAINER_NAME" | awk 'FNR == 2 {print $1}')
```

and replacing `YOUR_CONTAINER_NAME` with the name of the container you want to follow (eg yoma-webhooks-web). You can find the container name in the docker-compose.yaml.
