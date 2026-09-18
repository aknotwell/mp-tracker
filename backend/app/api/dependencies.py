"""Reusable FastAPI dependencies for authenticated and administrator routes."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import InvalidAccessTokenError, decode_access_token
from app.db import get_db_session
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


async def get_current_user(
    credentials: BearerCredentials,
    database: DatabaseSession,
    settings: AppSettings,
) -> User:
    """Validate a bearer token and load its current user from the database."""

    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise _authentication_error()
    try:
        claims = decode_access_token(credentials.credentials, settings)
    except InvalidAccessTokenError as error:
        raise _authentication_error() from error

    user = await database.get(User, claims.user_id)
    if user is None:
        raise _authentication_error()
    return user


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require an authenticated user whose current database row is an admin."""

    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator required")
    return current_user


def _authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(require_admin)]
