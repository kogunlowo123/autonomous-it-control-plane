"""In-memory sliding window rate limiter middleware.

Limits requests per client IP. For production, replace with Redis-backed
rate limiting (e.g., slowapi with Redis backend).
"""
from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter — {calls} requests per {period} seconds per IP."""

    def __init__(self, app: ASGIApp, calls: int = 100, period: int = 60) -> None:
        super().__init__(app)
        self.calls = calls
        self.period = period
        self._windows: dict[str, list[float]] = {}

    def _get_client_key(self, request: Request) -> str:
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Health and readiness endpoints bypass rate limiting
        if request.url.path in {"/api/v1/health", "/api/v1/readiness"}:
            return await call_next(request)

        client_key = self._get_client_key(request)
        now = time.monotonic()
        window_start = now - self.period

        # Clean expired entries and check window
        calls_in_window = [t for t in self._windows.get(client_key, []) if t > window_start]

        if len(calls_in_window) >= self.calls:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": self.calls,
                    "period_seconds": self.period,
                },
                headers={"Retry-After": str(self.period)},
            )

        calls_in_window.append(now)
        self._windows[client_key] = calls_in_window
        return await call_next(request)
