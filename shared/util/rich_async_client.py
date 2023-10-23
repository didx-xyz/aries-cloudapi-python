import logging
from typing import Optional

from fastapi import HTTPException
from httpx import AsyncClient, HTTPStatusError

logger = logging.getLogger(__name__)


# Async Client with built in error handling
class RichAsyncClient(AsyncClient):
    def __init__(
        self,
        *args,
        name: Optional[str] = None,
        verify=True,
        raise_status_error=True,
        **kwargs,
    ):
        self._name = (
            name + " - HTTP" if name else "HTTP"
        )  # prepend to exception messages to add context
        self.raise_status_error = raise_status_error

    async def post(self, url: str, **kwargs):
        try:
            response = await super().post(url, **kwargs)
            if self.raise_status_error:
                response.raise_for_status()  # Raise exception for 4xx and 5xx status codes
        except HTTPStatusError as e:
            code = e.response.status_code
            detail = f"{self._name} POST `{url}` failed. Status code: {code}. Response: `{e.response.text}`."
            logger.error(detail)
            raise HTTPException(status_code=code, detail=detail) from e
        return response

    async def get(self, url: str, **kwargs):
        try:
            response = await super().get(url, **kwargs)
            if self.raise_status_error:
                response.raise_for_status()
        except HTTPStatusError as e:
            code = e.response.status_code
            detail = f"{self._name} GET `{url}` failed. Status code: {code}. Response: `{e.response.text}`."
            logger.error(detail)
            raise HTTPException(status_code=code, detail=detail) from e
        return response

    async def delete(self, url: str, **kwargs):
        try:
            response = await super().delete(url, **kwargs)
            if self.raise_status_error:
                response.raise_for_status()
        except HTTPStatusError as e:
            code = e.response.status_code
            detail = f"{self._name} DELETE `{url}` failed. Status code: {code}. Response: `{e.response.text}`."
            logger.error(detail)
            raise HTTPException(status_code=code, detail=detail) from e
        return response

    async def put(self, url: str, **kwargs):
        try:
            response = await super().put(url, **kwargs)
            if self.raise_status_error:
                response.raise_for_status()
        except HTTPStatusError as e:
            code = e.response.status_code
            detail = f"{self._name} PUT `{url}` failed. Status code: {code}. Response: `{e.response.text}`."
            logger.error(detail)
            raise HTTPException(status_code=code, detail=detail) from e
        return response
