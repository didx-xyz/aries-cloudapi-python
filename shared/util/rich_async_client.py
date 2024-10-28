import asyncio
import logging
import ssl
from typing import List, Optional

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
        retries: int = 3,
        retry_on: List[int] = [503],
        **kwargs,
    ) -> None:
        super().__init__(verify=verify, *args, **kwargs)
        self.name = name + " - HTTP" if name else "HTTP"  # prepended to exceptions
        self.raise_status_error = raise_status_error
        self.retries = retries
        self.retry_on = retry_on

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

    async def _request_with_retries(self, method: str, url: str, **kwargs) -> Response:
        for attempt in range(self.retries):
            try:
                response = await getattr(super(), method)(url, **kwargs)
                return await self._handle_response(response)
            except HTTPStatusError as e:
                code = e.response.status_code
                if code in self.retry_on and attempt < self.retries - 1:
                    await asyncio.sleep(0.5)  # Wait before retrying
                    continue  # Retry the request
                await self._handle_error(e, url, method)

    async def post(self, url: str, **kwargs) -> Response:
        return await self._request_with_retries("post", url, **kwargs)

    async def get(self, url: str, **kwargs) -> Response:
        return await self._request_with_retries("get", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> Response:
        return await self._request_with_retries("delete", url, **kwargs)

    async def put(self, url: str, **kwargs) -> Response:
        return await self._request_with_retries("put", url, **kwargs)
