"""
Eaxample ws client connecting to all topics for acapy
"""
from fastapi_websocket_pubsub import PubSubClient
import asyncio
import os


PORT = os.getenv("PORT", "3010")


async def on_events(data, topic):
    print(f"{topic}: {data}")


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
        "revocation_registry",
    ]
    client = PubSubClient([], callback=on_events)

    async def on_data(data, topic):
        print(f"{topic}:\n", data)

    [client.subscribe(topic, on_data) for topic in topics]
    client.start_client(f"ws://0.0.0.0:{PORT}/pubsub")
    await client.wait_until_done()


asyncio.run(main())
