"""QueryLog middleware for logging all API requests.

Logs endpoint, method, IP, user_id, status_code, response_time, and errors
to MongoDB for analytics and auditing.
"""

import time
import logging
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app import db as db_module
from app.db import create_query_log_doc

logger = logging.getLogger(__name__)

# Paths excluded from logging
EXCLUDED_PATHS = {"/healthz", "/favicon.ico", "/static", "/docs", "/openapi.json", "/redoc"}


class QueryLogMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every request to MongoDB."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in EXCLUDED_PATHS):
            return await call_next(request)

        start_time = time.time()

        try:
            response = await call_next(request)
            response_time_ms = (time.time() - start_time) * 1000

            # Extract user_id from request state if available
            user_id = getattr(request.state, "user_id", None)

            # Log the query
            await self._log_query(
                endpoint=path,
                method=request.method,
                ip_address=request.client.host if request.client else None,
                user_id=user_id,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
            )

            return response
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            user_id = getattr(request.state, "user_id", None)

            await self._log_query(
                endpoint=path,
                method=request.method,
                ip_address=request.client.host if request.client else None,
                user_id=user_id,
                status_code=500,
                response_time_ms=response_time_ms,
                error=str(e),
            )
            raise

    async def _log_query(
        self,
        endpoint: str,
        method: str,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        status_code: int = 200,
        response_time_ms: float = 0.0,
        error: Optional[str] = None,
    ):
        """Insert query log document into MongoDB."""
        mongo_db = db_module.db
        if mongo_db is None:
            return
        try:
            doc = create_query_log_doc(
                endpoint=endpoint,
                method=method,
                ip_address=ip_address,
                user_id=user_id,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error=error,
            )
            # Fire-and-forget to avoid blocking response
            import asyncio
            asyncio.ensure_future(mongo_db.query_logs.insert_one(doc))
        except Exception as e:
            logger.warning(f"QueryLog write failed: {e}")
