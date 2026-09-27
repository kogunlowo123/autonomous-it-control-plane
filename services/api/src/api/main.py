"""Autonomous IT Control Plane API."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.auth import AuthMiddleware
from api.middleware.ratelimit import RateLimitMiddleware
from api.middleware.tenant import TenantMiddleware
from api.middleware.tracing import TracingMiddleware
from api.routes.v1 import change, health, incident
from api.settings import Settings

logger = logging.getLogger(__name__)


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _configure_tracing(settings: Settings) -> None:
    """Configure OpenTelemetry tracing if endpoint is configured."""
    if not settings.otel_exporter_otlp_endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create(
            {"service.name": "autonomous-it-api", "service.version": "0.1.0"}
        )
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry tracing configured")
    except ImportError:
        logger.warning("opentelemetry packages not available, tracing disabled")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings: Settings = app.state.settings
    _configure_logging(settings.log_level)
    _configure_tracing(settings)
    logger.info("Autonomous IT Control Plane API starting (version=0.1.0)")
    yield
    logger.info("Autonomous IT Control Plane API shutting down")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="Autonomous IT Control Plane",
        description=(
            "AI agents for autonomous IT operations, incident resolution, and change management. "
            "T1 agents resolve incidents autonomously; T2 changes require human approval."
        ),
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom middleware (applied in reverse order — last added = first executed)
    app.add_middleware(TracingMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(RateLimitMiddleware, calls=settings.rate_limit_calls, period=settings.rate_limit_period)
    app.add_middleware(AuthMiddleware, settings=settings)

    # Routes
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(change.router, prefix="/api/v1/change", tags=["change"])
    app.include_router(incident.router, prefix="/api/v1/incident", tags=["incident"])

    # Instrument with OpenTelemetry if available
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        pass

    return app


app = create_app()
