"""Authentication endpoint response schemas."""

from typing import Literal

from app.schemas.common import APIModel


class AccessTokenResponse(APIModel):
    """Short-lived bearer token returned only in a JSON response body."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
