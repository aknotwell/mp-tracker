# Authentication architecture

The application supports Google OpenID Connect only. It does not accept, hash, reset, or store user passwords.

## Session layers

Authentication uses two separate credentials:

1. A short-lived application JWT is sent as a bearer token for normal API requests. It contains the user ID, token ID, issuer, audience, issued time, expiration, and an `access` token type.
2. A random opaque refresh token is stored in an httpOnly cookie. Its SHA-256 hash—not the raw token—is stored in `auth_sessions`.

The refresh token starts with its session UUID so the backend can locate one row directly. The random secret after the UUID is still verified against the stored hash before the session is trusted.

## Rotation and revocation model

Each successful refresh will create a replacement session in the same `family_id`, revoke the previous session, and connect it through `replaced_by_session_id`. Presenting an already-revoked refresh token will be treated as possible token theft and will revoke its active session family.

The table also stores a hash of a separate CSRF token. Cookie-backed refresh and logout requests will have to submit the matching readable token in a request header.

## Google identity

Google's verified OpenID Connect `sub` claim maps to `users.google_subject`. Email is updated for display and administrator configuration, but it is never used as the durable login identity.

The future Google callback will request only `openid email profile` and validate the ID token's signature, issuer, audience, expiration, nonce, and verified-email claim before creating an application session.

## Configuration

Copy `backend/.env.example` to `backend/.env` and supply the Google client values before enabling live login. Production deployments must replace `APP_JWT_SECRET`, use HTTPS, and set `APP_COOKIE_SECURE=true`.

## Implemented authentication endpoints

- `GET /api/v1/auth/google/login` creates a private database login attempt and redirects to Google with authorization code, PKCE, state, and nonce parameters.
- `GET /api/v1/auth/google/callback` consumes the attempt once, validates Google's response, creates or updates the local user, sets refresh/CSRF cookies, and redirects to the frontend callback page.
- `POST /api/v1/auth/refresh` validates and rotates both browser credentials and returns a 15-minute access JWT.
- `POST /api/v1/auth/logout` revokes the browser session and clears both cookies.
- `GET /api/v1/auth/me` validates a bearer access JWT and returns the current database user.

OIDC transaction secrets are stored in `oidc_login_attempts`, never in a public/client-readable session. Attempts expire after ten minutes and are atomically marked used before Google's code exchange, preventing callback replay.

## Local Google setup

Create a Google Cloud OAuth client of type **Web application** and register this redirect URI exactly:

```text
http://localhost:8000/api/v1/auth/google/callback
```

Then place its values in the untracked `backend/.env`:

```dotenv
APP_GOOGLE_CLIENT_ID=your-client-id
APP_GOOGLE_CLIENT_SECRET=your-client-secret
APP_JWT_SECRET=replace-with-at-least-32-random-bytes
```

The backend authentication flow is implemented and tested with mocked Google responses. A real browser login still requires the Google Cloud values above and the frontend callback/bootstrap flow from a later frontend milestone.
