## 6: Server Sent Events
There are five different end-points to listen to server sent events (sse) on.
- `GET` `/sse/{wallet_id}`
- `GET` `/sse/{wallet_id}/{topic}`
- `GET` `/sse/{wallet_id}/{topic}/{desired_state}`
- `GET` `/sse/{wallet_id}/{topic}/{field}/{field_id}`
- `GET` `/sse/{wallet_id}/{topic}/{field}/{field_id}/{desired_state}`

Topics:
 - basic-messages
 - connections
 - proofs 
 - credentials
 - endorsements 
 - oob 
 - revocation 
 - issuer_cred_rev
 - problem_report

TODO: Explain the fields and their ids

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
