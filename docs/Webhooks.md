# Webhooks

The webhooks container serves as both a relay and storage for the webhooks,
enabling hooks to be retrieved at a later time. Furthermore, the webhooks
container processes the webhooks in two distinct ways.

Firstly, the hooks are converted into a shared format, which is shared with the
CloudAPI. This standardization is beneficial as the information and its format
in both the hooks and the CloudAPI are the same. This consistency allows for
easier client implementation as it only needs to anticipate a single data
structure from two endpoints, even if it's using v1 or v2 protocols.

Secondly, the webhooks are stored by topic and wallet ID. Consequently, the hooks
can be retrieved in these two ways - per wallet or per wallet per topic (but not
per topic - a choice made to reduce the data footprint).

There are also two ways to retrieve webhook data. The first method is the
classic HTTP request, potentially used multiple times to create a polling system.
Find the HTTP endpoints via the
[webhooks Swagger UI](http://webhooks.cloudapi.127.0.0.1.nip.io/docs) and create
your own polling mechanism. Alternatively, you can subscribe via the PubSub
mechanism (underlying Websockets) at the
[/pubsub endpoint](http://webhooks.cloudapi.127.0.0.1.nip.io/pubsub) by
specifying one or more topics. A brief example of how to do this in Python using
the [`fastapi_websocket_pubsub`](https://github.com/permitio/fastapi_websocket_pubsub)
package can be found in `webhooks/clients.example.py`.

>**_NOTE_**: The webhooks container is **NOT** intended to be directly exposed
to the world wide web, especially not via pubsub/websocket as there is NO
authentication mechanism in place. Exposing the websocket will leave anyone on
the internet able to read any webhook.

Valid topics are:

```python
topics = Literal[
    "basic-messages",
    "connections",
    "proofs",
    "credentials",
    "endorsements",
    "oob",
    "revocation",
    "issuer_cred_rev",
    "problem_report",
]
```

A client can subscribe to the webhooks via the CloudAPI (as opposed to directly
via the webhooks container). This requires only targeting the `/webhooks`
endpoint and optionally targeting the `/webhooks/{topic}` sub-route by suffixing
a topic. Using the authentication mechanism (see section below), the app
automatically extracts the required info about the wallet (i.e., the wallet id
and JWT) and retrieves only the associated webhooks with a particular wallet.
Failing to authenticate will return a 403 HTTP Error.

## Implementing your webhook listener

You can (assuming you are within the docker network) use a pubsub client (see
also `webhooks/clients.example.py`):

```python
from fastapi_websocket_pubsub import PubSubClient
import asyncio


async def on_events(data, topic):
    print(f"{topic}:\n{data}")


async def main():
    # Create a client and subscribe to topics
    topics = ["connections", "credentials", "proofs", "endorsements", "basic-messages"]
    client = PubSubClient([*topics], callback=on_events)

    client.start_client(f"ws://webhooks.cloudapi.127.0.0.1.nip.io/pubsub")
    await client.wait_until_done()


asyncio.run(main())
```

All webhooks are by default logged to the container's stdout, which can be handy
for debugging or development. You can easily pipe them into a file. On a Unix
machine, you can use this command to follow the webhook logs:

```bash
kubectl logs -f $(kubectl get pods \
  -l app.kubernetes.io/instance=governance-webhooks-web \
  -o jsonpath="{.items[0].metadata.name}")
```

### Non-Python options

Listening to webhooks the subscriber way (not long polling via HTTP) is not
limited to the Python example given above. In fact, all one needs is a
websocket-based RPC client.

Here are two examples:

```bash
websocat --exit-on-eof --text \
  ws://webhooks.cloudapi.127.0.0.1.nip.io/pubsub \
  exec:'{"request": {"method": "subscribe", "arguments": {"topics": ["proofs", "endorsements", "oob", "out_of_band", "connections", "basic-messages", "credentials"]}}}'
```

or

```bash
wscat -c ws://webhooks.cloudapi.127.0.0.1.nip.io \
  -x '{"request": {"method": "subscribe", "arguments": {"topics": ["proofs", "endorsements", "oob", "out_of_band", "connections", "basic-messages", "credentials"]}}}' \
  -w 99999
```

How this works is that either procedure instantiates a client connecting to the
websocket endpoint exposed via the webhooks container (_NOTE:_ You might have to
change the URI according to your setup of the webhooks relay). Both examples do
pretty much the same. However, [wscat](https://github.com/websockets/wscat) is
written in JavaScript whereas [websocat](https://github.com/vi/websocat) is
implemented in Rust. Both examples are given to illustrate that it really does
not matter what language one wishes to implement a listener in. After having
established a connection to the exposed endpoint, the `exec:` parameter and `-x`
flag mean execute. Execute, in this case, refers to sending the JSON payload to
the webhooks relay. It requests the endpoint to add the connection as a
subscriber to the topics array of the arguments key. You can pass any arguments
supported by the webhooks relay (see above). Passing an empty array under topics
means 'end the subscription'. By adding the `wallet_id` in the header is the way
to only receive hooks for a specific wallet.

## Server Sent Events

There are five different endpoints for listening to server-sent events (SSE).

- `GET` `/v1/sse/{wallet_id}`
- `GET` `/v1/sse/{wallet_id}/{topic}`
- `GET` `/v1/sse/{wallet_id}/{topic}/{desired_state}`
- `GET` `/v1/sse/{wallet_id}/{topic}/{field}/{field_id}`
- `GET` `/v1/sse/{wallet_id}/{topic}/{field}/{field_id}/{desired_state}`

Valid topics are same as noted above.

The `field` and `field_id` in the endpoints above serve as filters, and refers to
any field in the webhook event payload (excluding `wallet_id` and `topic`). The
name of the field of interest is passed in `{field}`, and the corresponding ID
or text that one wants to wait for is passed as `{field_id}`. i.e., you can pass
`connection_id` as `{field}`, and the ID of the connection you want to see the
events for as `{field_id}`. This will return only webhook events that match the
specified filter.

The routes that specify a `{desired_state}` will keep the stream open until a
single webhook event matches the specified filters, and then return that event.
The endpoints that don't specify a `{desired_state}`, will keep the stream open
and return all events matching the topic and optional field/field_id filters.

Here is an example Javascript implementation

```js
const EventSource = require('eventsource');
url = "http://cloudapi.127.0.0.1.nip.io/tenant-admin/v1/sse/<wallet_id>"

const headers = {
    'x-api-key':"tenant.<tenant/wallet_token>",
  };
const eventSource = new EventSource(url,{headers});
// Event listener for incoming server-sent events
eventSource.onmessage = (event) => {
  const eventData = JSON.parse(event.data);
  // log event
  console.log("EVENT ==> ", eventData)
};

// Event listener for handling errors
eventSource.onerror = (error) => {
  console.error('EventSource error:', error);
  // You can add error handling logic here if needed
};

console.log("<==============>")
```
