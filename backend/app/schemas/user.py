"""Safe user response schemas."""

from pydantic import ConfigDict

from app.schemas.common import ResourceSchema


class UserResponse(ResourceSchema):
    """Safe account fields; the provider subject stays server-side."""

    model_config = ConfigDict(from_attributes=True)

    email: str
    is_admin: bool
