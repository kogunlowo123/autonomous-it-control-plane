"""Tenant isolation middleware.

Resolves tenant ID from JWT claim, X-Tenant-ID header, or default.
"""
from __future__ import annotations

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolves and attaches tenant context to each request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Priority: X-Tenant-ID header > JWT claim > default
        tenant_id = (
            request.headers.get("X-Tenant-ID")
            or getattr(request.state, "tenant_id", None)
        )
        if not tenant_id:
            settings = request.app.state.settings
            tenant_id = settings.default_tenant_id

        request.state.tenant_id = tenant_id
        response = await call_next(request)
        response.headers["X-Tenant-ID"] = tenant_id
        return response
