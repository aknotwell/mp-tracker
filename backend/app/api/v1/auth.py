"""Google login and application-session HTTP endpoints."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from app.api.dependencies import AppSettings, CurrentUser, DatabaseSession
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import AccessTokenResponse
from app.schemas.user import UserResponse
from app.services.auth_sessions import (
    BrowserSession,
    InvalidCSRFTokenError,
    InvalidSessionError,
    RefreshTokenReuseError,
    create_browser_session,
    revoke_browser_session,
    rotate_browser_session,
)
from app.services.google_oidc import (
    InvalidOIDCResponseError,
    OIDCConfigurationError,
    consume_login_attempt,
    create_login_authorization,
    exchange_code_for_identity,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
CSRFHeader = Annotated[str | None, Header(alias="X-CSRF-Token")]


def _set_session_cookies(
    response: Response,
    browser_session: BrowserSession,
    settings: AppSettings,
) -> None:
    max_age = settings.refresh_session_days * 24 * 60 * 60
    response.set_cookie(
        settings.refresh_cookie_name,
        browser_session.refresh_token.raw,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/api/v1/auth",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        browser_session.csrf_token.raw,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def _clear_session_cookies(response: Response, settings: AppSettings) -> None:
    response.delete_cookie(settings.refresh_cookie_name, path="/api/v1/auth")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


@router.get("/google/login", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def google_login(database: DatabaseSession, settings: AppSettings) -> RedirectResponse:
    """Create private login state and redirect the browser to Google."""

    try:
        authorization = create_login_authorization(settings)
    except OIDCConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error

    database.add(authorization.attempt)
    await database.commit()
    return RedirectResponse(authorization.url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/google/callback", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def google_callback(
    database: DatabaseSession,
    settings: AppSettings,
    code: str,
    state: str,
) -> RedirectResponse:
    """Validate Google's response and create a local browser session."""

    try:
        attempt = await consume_login_attempt(database, state)
        # Commit the one-time consumption before making an external request. A failed
        # code exchange requires starting a new login instead of replaying this state.
        await database.commit()
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            identity = await exchange_code_for_identity(
                code,
                attempt,
                settings,
                http_client,
            )
    except OIDCConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error
    except InvalidOIDCResponseError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed",
        ) from error

    user = await database.scalar(select(User).where(User.google_subject == identity.subject))
    if user is None:
        user = User(
            google_subject=identity.subject,
            email=identity.email,
            is_admin=identity.email in settings.normalized_admin_emails,
        )
        database.add(user)
    else:
        user.email = identity.email
        user.is_admin = user.is_admin or identity.email in settings.normalized_admin_emails

    browser_session = create_browser_session(user, settings)
    database.add(browser_session.model)
    await database.commit()

    callback_url = f"{str(settings.frontend_origin).rstrip('/')}/auth/callback"
    response = RedirectResponse(callback_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    _set_session_cookies(response, browser_session, settings)
    return response


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_access_token(
    request: Request,
    database: DatabaseSession,
    settings: AppSettings,
    csrf_header: CSRFHeader = None,
) -> JSONResponse:
    """Rotate valid browser credentials and return a fresh access JWT."""

    raw_refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not raw_refresh_token or not csrf_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    try:
        replacement = await rotate_browser_session(
            database,
            raw_refresh_token,
            csrf_header,
            settings,
        )
        await database.commit()
    except InvalidCSRFTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token"
        ) from error
    except RefreshTokenReuseError:
        await database.commit()
        response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid session"},
        )
        _clear_session_cookies(response, settings)
        return response
    except InvalidSessionError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        ) from error

    token = AccessTokenResponse(
        access_token=create_access_token(replacement.model.user_id, settings),
        expires_in=settings.access_token_minutes * 60,
    )
    response = JSONResponse(content=token.model_dump())
    _set_session_cookies(response, replacement, settings)
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    database: DatabaseSession,
    settings: AppSettings,
    csrf_header: CSRFHeader = None,
) -> Response:
    """Revoke the current browser session and clear its cookies."""

    raw_refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if raw_refresh_token:
        if not csrf_header:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token",
            )
        try:
            await revoke_browser_session(database, raw_refresh_token, csrf_header)
            await database.commit()
        except InvalidCSRFTokenError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token"
            ) from error
        except InvalidSessionError:
            await database.rollback()

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookies(response, settings)
    return response


@router.get("/me", response_model=UserResponse)
async def current_user(user: CurrentUser) -> User:
    """Return the database-backed identity for the current access token."""

    return user
