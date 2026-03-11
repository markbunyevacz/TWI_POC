"""Simple in-memory rate limiter for the bot messaging endpoint.

Uses a per-user sliding-window counter stored in a dict.  This is
sufficient for a single-instance PoC.  For multi-replica production
deployments, replace with a Redis-backed counter.
"""

import logging
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Default: 20 requests per 60-second window per user/IP
_DEFAULT_MAX_REQUESTS = 20
_DEFAULT_WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter scoped to the bot messages endpoint.

    Only ``POST /api/messages`` and ``POST /api/telegram/webhook`` are
    rate-limited.  Other endpoints (health, docs, document API) are not
    affected.
    """

    def __init__(
        self,
        app,
        max_requests: int = _DEFAULT_MAX_REQUESTS,
        window_seconds: int = _DEFAULT_WINDOW_SECONDS,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # user_key → list of request timestamps
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method != "POST" or path not in (
            "/api/messages",
            "/api/telegram/webhook",
        ):
            return await call_next(request)

        key = self._get_key(request)
        now = time.monotonic()

        # Prune timestamps outside the current window
        bucket = self._buckets[key]
        cutoff = now - self.window_seconds
        self._buckets[key] = [t for t in bucket if t > cutoff]
        bucket = self._buckets[key]

        if len(bucket) >= self.max_requests:
            logger.warning("Rate limit exceeded for key=%s", key)
            return Response(
                status_code=429,
                content="Too many requests. Please wait before trying again.",
            )

        bucket.append(now)
        return await call_next(request)

    @staticmethod
    def _get_key(request: Request) -> str:
        """Derive a rate-limit key from the request.

        Uses the ``X-Forwarded-For`` header (set by Azure Front Door /
        Container Apps ingress) or falls back to the client host IP.
        """
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"
