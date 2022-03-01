from typing import Any, Dict, Union
from fastapi import HTTPException


class CloudApiException(HTTPException):
    """Class that represents a cloud api error"""

    def __init__(
        self,
        detail: Union[str, Dict[str, Any]],
        status_code: int = 500,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)
