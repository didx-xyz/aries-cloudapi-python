from typing import Optional

from fastapi import HTTPException
from httpx import AsyncClient, HTTPStatusError


# Async Client with built in error handling
class RichAsyncClient(AsyncClient):
    def __init__(self, *args, name: Optional[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._name = (
            name + " - HTTP" if name else "HTTP"
        )  # prepend to exception messages to add context

    async def post(self, url: str, **kwargs):
        try:
            response = await super().post(url, **kwargs)
            response.raise_for_status()  # Raise exception for 4xx and 5xx status codes
        except HTTPStatusError as e:
            code = e.response.status_code
            raise HTTPException(
                detail=f"{self._name} post to `{url}` failed. Status code: {code}. Response: {e.response.text}",
                status_code=code,
            raise HTTPException(status_code=code) from e
        return response

    async def get(self, url: str, **kwargs):
        try:
            response = await super().get(url, **kwargs)
            response.raise_for_status()
        except HTTPStatusError as e:
            code = e.response.status_code
            raise HTTPException(
                detail=f"{self._name} get to `{url}` failed. Status code: {code}. Response: {e.response.text}",
                status_code=code,
            raise HTTPException(status_code=code) from e
        return response

    async def delete(self, url: str, **kwargs):
        try:
            response = await super().delete(url, **kwargs)
            response.raise_for_status()
        except HTTPStatusError as e:
            code = e.response.status_code
            raise HTTPException(
                detail=f"{self._name} delete to `{url}` failed. Status code: {code}. Response: {e.response.text}",
                status_code=code,
            raise HTTPException(status_code=code) from e
        return response

    async def put(self, url: str, **kwargs):
        try:
            response = await super().put(url, **kwargs)
            response.raise_for_status()
        except HTTPStatusError as e:
            code = e.response.status_code
            raise HTTPException(
                detail=f"{self._name} put to `{url}` failed. Status code: {code}. Response: {e.response.text}",
                status_code=code,
            raise HTTPException(status_code=code) from e
        return response
