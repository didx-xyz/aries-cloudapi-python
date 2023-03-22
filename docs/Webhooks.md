# Webhooks

The webhooks container serves as a relay and storage for the webhooks. This way hooks can be retrieved at a later time. On top of that, the webhooks container processes the webhooks in two ways.

Firstly, the hooks are converted into a shared format, shared with the cloud api. This is handy because the information and its format in both the hooks as well as the CloudAPI are the same. This allows for easier implementation of clients (having to expect a single data structure from the two endpoints).

Secondly, the webhooks are stored by topic and wallet ID. That way the hooks can be retrieved in these two ways - per wallet or per wallet per topic (but not per topic - a choice made to reduce data footprint).

There are also two ways to retrieve webhook data. The first way is tha classic http request and multiple thereof aka polling. Find the http endpoints via the [webhooks SwaggerUI](http://localhost:3010/docs) and roll your own polling mechanism. You can also subscribe to via PubSub mechanism (Websockets under the hood) under the [/pubsub endpoint](http://localhost:3010/pubsub) and specifying a, or several, topic(s). There is a short example of how to do that in python using the [`fastapi_websocket_pubsub`](https://github.com/permitio/fastapi_websocket_pubsub) package you can find in `webhooks/clients.example.py`.

**_NOTE_**: The webhooks container is **NOT** intended to be exposed to the ww directly, especially not via pubsub/websocket as there is NO auth mechanism in place. Exposing the websocket will leave anyone on the www able to read any webhook.

Valid topics are:

```python
topics = Literal[
    "basic-messages", "connections", "proofs", "credentials", "endorsements", "oob", "revocation"
]
```

A client can subscribe to the webhooks via the CloudAPI (as opposed to directly via the webhooks container). This requires only targeting the `/webhooks` endpoint and optionally targeting the `/webhooks/{topic}` sub-route by suffixing a topic. Using the auth mechanism (see section below), the app automatically extracts the required info about the wallet (i.e the wallet id and JWT) and retrieves only the associated webhooks with a particular wallet. Failing to authenticate will return a 403 HTTP Error.

## Rolling your webhook listener

You can (given you are within the docker network) use a pubsub client (see also `webhooks/clients.example.py`):

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

All (and this can be handy for debugging or development as you just get all webhooks printed to stdout - you can also easily pipe then into a file, btw) webhooks are by default logged to the containers stdout. On a Unix machine you should be able to use this command to follow the webhook logs:

```bash
docker logs --follow $(docker ps -f name="governance-webhooks-web" | awk 'FNR == 2 {print $1}')
```

### Non-Python options

Listening to webhooks the subscriber way (not long polling via http) is pnot limited to the python example given above. In fact, all one needs is a websocket-based RPC client.

Here are two examples from the terminal:

```bash
websocat -E --text ws://127.0.0.1:3010/pubsub exec:'{"request": {"method": "subscribe", "arguments": {"topics": ["proofs", "endorsements", "oob", "out_of_band", "connections", "basic-messages", "credentials"]}}}'
```

or

```bash
wscat -c ws://127.0.0.1:3010 -x '{"request": {"method": "subscribe", "arguments": {"topics": ["proofs", "endorsements", "oob", "out_of_band", "connections", "basic-messages", "credentials"]}}}' -w 99999
```

How this works is that either procedure instantiates a client connecting to the websocket endpoint exposed via the webhooks container (_NOTE:_ You might have to change the uri according to your setup of the webhooks relay). Both examples do pretty much the same. However, [Wscat](https://github.com/websockets/wscat) is written in Javascript whereas [websocat](https://github.com/vi/websocat) is implemented in Rust. Both examples are given to illustrate that it really does not matter what language one wishes to implement a listener in. After having established a connection to the exposed endpoint the `exec:` parameter and `-x` flag mean execute. Execute in this case refers to sending the JSON payload to the webhooks relay. It requests the endpoint to add the connection as a subscriber to the topics array of the arguments key. You can pass any arguments supported by the webhooks relay (see above). Passing an empty array under topics means 'end the subscription'. By Adding the `wallet_id` in the header is the way to only receive hooks for a specific wallet.

#### Javascript example

Here's a simple example in javascript using a single dependency (`ws`):

```javascript
const WebSocket = require("ws");

const ws = new WebSocket("ws://127.0.0.1:3010/pubsub");

ws.on("open", () => {
  ws.send(
    '{"request": {"method": "subscribe", "arguments": {"topics": ["proofs", "endorsements", "oob", "out_of_band", "connections", "basic-messages", "credentials"]}}}'
  );
  setTimeout(() => {
    ws.close(); // close after 99999 seconds
  }, 99999);
});

ws.on("message", (data) => {
  console.log(data.toString());
});
```

In order to use this:

- Install `ws` dependency with
  - `npm i ws` OR `yarn add ws` (you can add the `--save-dev` or `-D` flags to install as dev dependencies, or `-g` and `global` respectively to install globally)
- Save the script above to a file (eg wslisten.js)
- Run the script with node `node wslisten.js`
