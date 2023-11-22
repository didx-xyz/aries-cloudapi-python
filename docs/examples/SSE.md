## 6: Server Sent Events

There are five different endpoints for listening to server-sent events (SSE).

- `GET` `/sse/{wallet_id}`
- `GET` `/sse/{wallet_id}/{topic}`
- `GET` `/sse/{wallet_id}/{topic}/{desired_state}`
- `GET` `/sse/{wallet_id}/{topic}/{field}/{field_id}`
- `GET` `/sse/{wallet_id}/{topic}/{field}/{field_id}/{desired_state}`

The `field` and `field_id` in the endpoints above refer to any fields in the events, excluding `wallet_id`, `topic`, or `state`, along with their corresponding IDs. i.e. You can pass `connection_id` and the ID of the connection if you only want to see events on a specific connection.

Topics:
 - connections
 - proofs 
 - credentials
 - oob 
 - revocation 
 - endorsements 
 - issuer_cred_rev
 - problem_report
 - basic-messages


Here is example Javascript implementation

```js
const EventSource = require('eventsource');
url = "http://localhost:8100/sse/<wallet_id>"

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
