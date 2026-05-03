"""Stateless CSRF protection middleware for FastAPI + HTMX.

Uses the double-submit cookie pattern with HMAC-signed tokens:
1. A CSRF token (HMAC-signed timestamp+nonce) is set as a readable cookie
2. HTMX reads the cookie and sends it as X-CSRFToken header on every mutation
3. Non-HTMX forms embed the token as a hidden <input name="csrf_token">
4. Middleware validates the HMAC signature — NO server-side store needed

Key advantages over in-memory store:
  ✅ Survives server restarts / --reload cycles (no token invalidation)
  ✅ Scales across multiple workers/processes without shared state
  ✅ Tokens self-expire via embedded timestamp (configurable TTL)
  ✅ HMAC prevents forgery even without a database

JSON API requests (Content-Type: application/json) are exempt from CSRF
because browsers cannot trigger cross-origin JSON POSTs via simple forms.
"""

import hashlib
import hmac
import logging
import os
import secrets
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ── Module-level flag to bypass CSRF (used in tests) ──
CSRF_ENABLED = True

# ── Signing secret — stable across restarts if env var is set ──
_CSRF_SECRET: str = (
    os.getenv("CSRF_SECRET")
    or os.getenv("SESSION_SECRET")
    or os.getenv("JWT_SECRET")
    or secrets.token_hex(32)
)

# Token valid for 4 hours
_TOKEN_TTL: int = 4 * 3600

COOKIE_NAME = "csrftoken"
HEADER_NAME = "X-CSRFToken"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


# ── Token helpers ────────────────────────────────────────────────

def _generate_token() -> str:
    """Generate a stateless HMAC-signed CSRF token.

    Format:  <ts_hex>.<rand_hex>.<hmac_hex>
    The HMAC covers (ts + nonce), so any tampering is detectable.
    """
    ts = format(int(time.time()), "x")   # hex unix timestamp
    rand = secrets.token_hex(16)         # random nonce — prevents replay / brute-force
    payload = f"{ts}.{rand}"
    sig = hmac.new(
        _CSRF_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{sig}"


def _validate_token(token: str) -> bool:
    """Validate a stateless HMAC-signed CSRF token.

    Returns True iff the token:
      - Has the correct 3-part structure
      - Has a valid HMAC (i.e. was issued by this server secret)
      - Has not expired (within _TOKEN_TTL seconds of issuance)
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return False
        ts_hex, rand, received_sig = parts
        # Check expiry
        if time.time() - int(ts_hex, 16) > _TOKEN_TTL:
            return False
        # Verify HMAC
        payload = f"{ts_hex}.{rand}"
        expected_sig = hmac.new(
            _CSRF_SECRET.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_sig, received_sig)
    except Exception:
        return False


# ── Middleware ───────────────────────────────────────────────────

class CSRFMiddleware(BaseHTTPMiddleware):
    """Stateless CSRF middleware using double-submit HMAC cookies.

    Safe methods (GET, HEAD, OPTIONS):
      - Always refresh the cookie if missing or expired.
      - A fresh valid token guarantees the next POST won't be rejected
        even after a server restart / reload.

    Mutating methods (POST, PUT, PATCH, DELETE):
      - JSON bodies are exempt (CORS protects them).
      - Form bodies must supply the cookie value via:
          a) X-CSRFToken request header  (HTMX htmx:configRequest handler)
          b) csrf_token hidden form field (non-HTMX / native submit forms)
    """

    async def dispatch(self, request: Request, call_next):
        if not CSRF_ENABLED:
            return await call_next(request)

        # ── Safe methods: process then refresh cookie if needed ──
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            existing = request.cookies.get(COOKIE_NAME, "")
            # Refresh if missing OR if the token has expired / is invalid
            # (covers the case where server restarted with a new _CSRF_SECRET)
            if not existing or not _validate_token(existing):
                token = _generate_token()
                response.set_cookie(
                    key=COOKIE_NAME,
                    value=token,
                    httponly=False,      # JS must read it for HTMX / hidden field injection
                    samesite="strict",
                    secure=False,        # Set True in production (HTTPS only)
                    max_age=_TOKEN_TTL,
                    path="/",
                )
            return response

        # ── JSON API requests are CSRF-exempt ──
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            return await call_next(request)

        # ── Form submissions: validate token ──
        cookie_token = request.cookies.get(COOKIE_NAME)
        header_token = request.headers.get(HEADER_NAME)

        # Fallback: accept token from hidden form field for native .submit() calls
        if not header_token:
            try:
                form_data = await request.form()
                header_token = form_data.get("csrf_token")
            except Exception:
                pass

        if not cookie_token or not header_token:
            logger.warning("CSRF rejected: token missing (path=%s)", request.url.path)
            return Response(status_code=403, content="CSRF token missing")

        if not _validate_token(cookie_token):
            logger.warning("CSRF rejected: cookie token invalid/expired (path=%s)", request.url.path)
            return Response(status_code=403, content="CSRF token invalid or expired — please refresh the page")

        if not hmac.compare_digest(cookie_token, header_token):
            logger.warning("CSRF rejected: token mismatch (path=%s)", request.url.path)
            return Response(status_code=403, content="CSRF token mismatch")

        return await call_next(request)
