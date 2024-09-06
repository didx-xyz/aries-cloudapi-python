import json
from typing import Any, Dict

from httpx import Timeout

from shared import WAYPOINT_URL
from shared.log_config import get_logger
from shared.util.rich_async_client import RichAsyncClient

logger = get_logger(__name__)

base_url = f"{WAYPOINT_URL}/waypoint"

DEFAULT_LISTENER_TIMEOUT = 30  # seconds


class WaypointListener:
    """
    A class to listen to waypoint events.
    """

    def __init__(
        self,
        wallet_id: str,
        topic: str,
    ):
        logger.debug(
            "Starting WaypointListener for wallet id `{}` and topic `{}`",
            wallet_id,
            topic,
        )
        self.wallet_id = wallet_id
        self.topic = topic

    async def wait_for_event(
        self,
        field,
        field_id,
        desired_state,
        group_id: str,
        timeout: int = DEFAULT_LISTENER_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        Start listening for waypoint event. When an event is received that matches the specified parameters.
        """
        url = f"{base_url}/{self.wallet_id}/{self.topic}/{field}/{field_id}/{desired_state}"

        timeout = Timeout(timeout)
        async with RichAsyncClient(timeout=timeout) as client:
            async with client.stream(
                "GET", url, params={"group_id": group_id}
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        return data["payload"]
                    elif line == "" or line.startswith(": ping"):
                        pass  # ignore newlines and pings
                    else:
                        logger.warning("Unexpected SSE line: {}", line)

        raise WaypointListenerTimeout(
            "Requested filtered event was not returned by server."
        )


class WaypointListenerTimeout(Exception):
    """Exception raised when the Listener times out waiting for a matching event."""
