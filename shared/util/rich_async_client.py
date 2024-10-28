import logging
import ssl
from typing import Optional

from fastapi import HTTPException
from httpx import AsyncClient, HTTPStatusError, Response

logger = logging.getLogger(__name__)

ssl_context = ssl.create_default_context()


# Async Client with built in error handling and re-using SSL certs
class RichAsyncClient(AsyncClient):
    def __init__(
        self,
        *args,
        name: Optional[str] = None,
        verify=ssl_context,
        raise_status_error=True,
        **kwargs,
    ) -> None:
        super().__init__(verify=verify, *args, **kwargs)
        self.name = (
            name + " - HTTP" if name else "HTTP"
        )  # prepend to exception messages to add context
        self.raise_status_error = raise_status_error

    async def _handle_response(self, response: Response) -> Response:
        if self.raise_status_error:
            response.raise_for_status()  # Raise exception for 4xx and 5xx status codes
        return response

    async def _handle_error(self, e: HTTPStatusError, url: str, method: str) -> None:
        code = e.response.status_code
        message = e.response.text
        log_message = f"{self.name} {method} `{url}` failed. Status code: {code}. Response: `{message}`."
        logger.error(log_message)
        raise HTTPException(status_code=code, detail=message) from e

    async def post(self, url: str, **kwargs) -> Response:
        try:
            response = await super().post(url, **kwargs)
            return await self._handle_response(response)
        except HTTPStatusError as e:
            await self._handle_error(e, url, "POST")

    async def get(self, url: str, **kwargs) -> Response:
        try:
            response = await super().get(url, **kwargs)
            return await self._handle_response(response)
        except HTTPStatusError as e:
            await self._handle_error(e, url, "GET")

    async def delete(self, url: str, **kwargs) -> Response:
        try:
            response = await super().delete(url, **kwargs)
            return await self._handle_response(response)
        except HTTPStatusError as e:
            await self._handle_error(e, url, "DELETE")

    async def put(self, url: str, **kwargs) -> Response:
        try:
            response = await super().put(url, **kwargs)
            return await self._handle_response(response)
        except HTTPStatusError as e:
            await self._handle_error(e, url, "PUT")
