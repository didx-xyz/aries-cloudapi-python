"""
Eaxample ws client connecting to all topics for acapy
"""
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
    client = PubSubClient(["ALL_WEBHOOKS"], callback=on_events)

    """
    # You can also register it using the commented code below
    async def on_data(data, topic):
        print(f"{topic}:\n", data)

    [client.subscribe(topic, on_data) for topic in topics]
    """

    client.start_client(f"ws://{URL}:{PORT}/pubsub")
    print("Started")
    await client.wait_until_done()


asyncio.run(main())
