"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.products import router as products_router
from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.database import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    resolved_settings = settings or Settings.from_environment()
    configure_logging(resolved_settings.log_level)
    database = Database(resolved_settings.database_path)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database.initialize()
        application.state.database = database
        yield

    application = FastAPI(
        title="Products REST API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(products_router, prefix=resolved_settings.api_prefix)
    return application


app = create_app()
