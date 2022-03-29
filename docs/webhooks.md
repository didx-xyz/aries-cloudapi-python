### Webhooks

The webhooks container serves as a relay and storage for the webhooks. This way hooks can be retrieved at a later time. On top of that, the webhooks container processes the webhooks in two ways.

Firstly, the hooks are converted into a shared format, shared with the cloud api. This is handy because the information and its format in both the hooks as well as the CloudAPI are the same. This allows for easier implementation of clients (having to expect a single data structure from the two endpoints).

Secondly, the webhooks are stored by topic and wallet ID. That way the hooks can be retrieved in these two ways - per wallet or per wallet per topic (but not per topic - a choice made to reduce data footprint).

There are also two ways to retrieve webhook data. The first way is tha classic http request and multiple thereof aka polling. Find the http endpoints via the [webhooks SwaggerUI](http://localhost:3010/docs) and roll your own polling mechanism. You can also subscribe to via PubSub mechanism (Websockets under the hood) under the [/pubsub endpoint](http://localhost:3010/pubsub) and specifying a, or several, topic(s). There is a short example of how to do that in python using the [`fastapi_websocket_pubsub`](https://github.com/permitio/fastapi_websocket_pubsub) package you can find in `webhooks/clients.example.py`.

Valid topics are:

```python
topics = Literal[
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
    "present_proof_v2_0",
    "revocation_registry",
]
```

All (and this can be handy for debugging or development as you just get all webhooks printed to stdout - you can also easily pipe then into a file, btw) webhooks are by default logged to the containers stdout. On a Unix machine you should be able to use this command to follow the webhook logs:

```bash
docker logs --follow $(docker ps -f name="yoma-webhooks-web" | awk 'FNR == 2 {print $1}')
```
