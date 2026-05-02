"""CSRF protection middleware for FastAPI + HTMX.

Uses the double-submit cookie pattern:
1. A CSRF token is set as a cookie (httponly=False, same_site=strict)
2. HTMX reads the cookie and sends it as an X-CSRFToken header
3. Middleware validates the header matches the cookie on mutating form requests

JSON API requests (Content-Type: application/json) are exempt from CSRF
because browsers cannot trigger cross-origin JSON POSTs via simple HTML forms.
"""

import secrets
from datetime import datetime, timedelta, timezone
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Module-level flag to bypass CSRF (used in tests)
CSRF_ENABLED = True


class CSRFTokens:
    """In-memory store for issued CSRF tokens (with expiry)."""

    def __init__(self, ttl_seconds: int = 3600):
        self._tokens: dict[str, datetime] = {}
        self._ttl = ttl_seconds

    def generate(self) -> str:
        """Generate a new CSRF token."""
        token = secrets.token_urlsafe(32)
        self._tokens[token] = datetime.now(timezone.utc) + timedelta(seconds=self._ttl)
        self._cleanup()
        return token

    def validate(self, token: str) -> bool:
        """Validate a CSRF token."""
        self._cleanup()
        expiry = self._tokens.get(token)
        if expiry is None:
            return False
        return datetime.now(timezone.utc) < expiry

    def _cleanup(self):
        """Remove expired tokens."""
        now = datetime.now(timezone.utc)
        expired = [t for t, exp in self._tokens.items() if exp < now]
        for t in expired:
            del self._tokens[t]


_csrf_store = CSRFTokens()

COOKIE_NAME = "csrftoken"
HEADER_NAME = "X-CSRFToken"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
FORM_CONTENT_TYPES = {
    "application/x-www-form-urlencoded",
    "multipart/form-data",
}


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware that issues CSRF cookies and validates tokens on mutating form requests.

    JSON API requests are exempt (browsers can't trigger cross-origin JSON POSTs).
    """

    async def dispatch(self, request: Request, call_next):
        if not CSRF_ENABLED:
            return await call_next(request)

        if request.method in SAFE_METHODS:
            response = await call_next(request)
            if not request.cookies.get(COOKIE_NAME):
                token = _csrf_store.generate()
                response.set_cookie(
                    key=COOKIE_NAME,
                    value=token,
                    httponly=False,
                    samesite="strict",
                    secure=False,
                    max_age=3600,
                    path="/",
                )
            return response

        # Skip CSRF for JSON API requests (CORS protects against CSRF for JSON)
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            return await call_next(request)

        # For form submissions (multipart or urlencoded): validate CSRF token
        cookie_token = request.cookies.get(COOKIE_NAME)
        header_token = request.headers.get(HEADER_NAME)

        if not cookie_token or not header_token:
            return Response(status_code=403, content="CSRF token missing")

        if not _csrf_store.validate(cookie_token):
            return Response(status_code=403, content="CSRF token expired")

        if not secrets.compare_digest(cookie_token, header_token):
            return Response(status_code=403, content="CSRF token mismatch")

        return await call_next(request)
