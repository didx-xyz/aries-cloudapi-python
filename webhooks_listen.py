import json
from fastapi_websocket_pubsub import PubSubClient
import pprint
import asyncio

async def on_events(data, topic):
    # print(f"{topic}:\n{data}")
    data = json.loads(data)
    print(f"\n{data['topic']}:")
    pprint.pprint(data['payload'], indent=2)

async def main():
    # Create a client and subscribe to topics
    topics = [
        "connections",
        "credentials",
        "out_of_band",
        "oob",
        "proofs",
        "endorsements",
        "basic-messages"
    ]
    client = PubSubClient([*topics], callback=on_events)

    client.start_client(f"ws://127.0.0.1:3010/")
    await client.wait_until_done()

asyncio.run(main())