# Webhooks/Event Consumption

## Primary Method: NATS

The recommended and most efficient way to consume events is through our NATS implementation. NATS provides a robust,
scalable solution for event streaming and processing. For detailed information about consuming events from our NATS implementation,
please refer to this document: [NATS](NATS.md).

## Alternative: Waypoint Service

The Waypoint service provides a specialized Server-Sent Events (SSE) endpoint for cases where you need to wait for a specific
event that you know is coming. This is particularly useful when you need to track the state change of a specific entity
and have all the necessary filter information.

The Waypoint service exposes a single SSE endpoint, via the main app, for event streaming:

- `GET` `/v1/sse/{wallet_id}/{topic}/{field}/{field_id}/{desired_state}`

This endpoint is designed for targeted event retrieval where you can specify exact filters to wait for a particular event.

### How to use

The endpoint requires specific filter parameters:

- `wallet_id`: Identifier for the specific wallet
- `topic`: The event topic to subscribe to
- `field`: Filter field from the event payload
- `field_id`: Specific value for the filter field
- `desired_state`: The desired state of the event

For example, if you're waiting for a specific connection to reach the 'completed' state, you would use:

- `field`: "connection_id"
- `field_id`: "<your_connection_id>"
- `desired_state`: "completed"

The stream will remain open until the desired event (matching the filters) is found and returned, at which point the stream
will be closed.

Valid topics include:

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

## Implementing Your Event Listener

Here's an example of how to implement an event listener using JavaScript:

```javascript
const EventSource = require('eventsource');

const wallet_id = '<your_wallet_id>';
const url = `http://cloudapi.127.0.0.1.nip.io/tenant-admin/v1/sse/${wallet_id}/proofs/connections/<some_id>/done`;

const headers = {
  'x-api-key': 'tenant.<tenant/wallet_token>',
};

const eventSource = new EventSource(url, { headers });

// Event listener for incoming server-sent events
eventSource.onmessage = (event) => {
  const eventData = JSON.parse(event.data);
  console.log("EVENT ==> ", eventData);
};

// Event listener for handling errors
eventSource.onerror = (error) => {
  console.error('EventSource error:', error);
  // Add your error handling logic here
};

console.log("Listening for events...");
```

This script establishes a connection to the SSE endpoint and listens for incoming events. When an event is received,
it's logged to the console. Error handling is also implemented to manage any issues that may arise during the connection.

>**_NOTE_**: Ensure that you replace `<your_wallet_id>` with the actual wallet ID and use the appropriate `x-api-key`
for authentication.

## Authentication

The Waypoint service requires authentication to access the SSE endpoint. This is managed through the `x-api-key` header
in the request. The key should be in the format `tenant.<tenant/wallet_token>`. Failing to provide valid authentication
will result in a 403 HTTP Error.
