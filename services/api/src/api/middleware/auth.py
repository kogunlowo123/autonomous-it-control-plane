"""JWT authentication middleware.

Validates Bearer tokens on all non-exempt paths.
Supports HS256 (for testing) and RS256 (production).
"""
from __future__ import annotations

import logging
from typing import Callable

import jwt
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Paths that do not require authentication
UNAUTHENTICATED_PATHS: frozenset[str] = frozenset({
    "/api/v1/health",
    "/api/v1/readiness",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
})


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates JWT Bearer tokens on protected endpoints."""

    def __init__(self, app: ASGIApp, settings: object) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Pass through unauthenticated paths
        if request.url.path in UNAUTHENTICATED_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header. Expected: Bearer <token>"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Empty Bearer token"})

        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=["HS256", "RS256"],
                options={"verify_exp": True},
            )
            request.state.user = payload.get("sub", "anonymous")
            request.state.roles = payload.get("roles", [])
            request.state.tenant_id = payload.get("tenant_id", self.settings.default_tenant_id)
            request.state.jwt_tier = payload.get("tier", "T1")
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token expired"})
        except jwt.InvalidAudienceError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token audience"})
        except jwt.InvalidTokenError as exc:
            logger.debug("JWT validation failed: %s", exc)
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        return await call_next(request)
