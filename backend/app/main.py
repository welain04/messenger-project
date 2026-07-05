from pathlib import Path
import logging

from fastapi import APIRouter, FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException

from . import db
from .config import get_settings
from .errors import validation_exception_handler
from .middleware import JWTUserMiddleware
from .security_headers import SecurityHeadersMiddleware
from .routers import admin, auth, chats, files, messages, notifications, uploads, users
from .sentry_setup import init_sentry
from .services.storage.factory import create_storage_service

logger = logging.getLogger("messenger")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    init_sentry(settings)
    db.init_db()
    docs_kwargs: dict = {}
    if settings.is_production:
        docs_kwargs = {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(
        title="Online School Messenger API",
        version="1.0.0",
        description="Messenger backend for an online school.",
        **docs_kwargs,
    )

    try:
        app.state.storage_service = create_storage_service(settings)
        logger.info("StorageService initialized provider=%s", settings.STORAGE_PROVIDER)
    except ValueError as exc:
        logger.warning("StorageService not initialized: %s", exc)
        app.state.storage_service = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(JWTUserMiddleware)
    if settings.security_headers_enabled:
        app.add_middleware(SecurityHeadersMiddleware)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(auth.router)
    api_v1.include_router(users.router)
    api_v1.include_router(chats.router)
    api_v1.include_router(messages.router)
    api_v1.include_router(uploads.router)
    api_v1.include_router(files.router)
    api_v1.include_router(notifications.router)
    api_v1.include_router(admin.router)

    # Вспомогательные эндпоинты для E2E-тестов — только при явном включении.
    if settings.ENABLE_TEST_ENDPOINTS:
        from .routers import test_support

        api_v1.include_router(test_support.router)
        logger.warning("Test-support endpoints are ENABLED (/api/v1/_test/*)")

    app.include_router(api_v1)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    if settings.SENTRY_DSN.strip():
        debug_key = settings.SENTRY_DEBUG_KEY.strip()
        if debug_key:
            logger.info("Sentry debug test route: /health/sentry-test")

            @app.get("/health/sentry-test", include_in_schema=False)
            def sentry_test(key: str = Query(...)) -> None:
                if key != get_settings().SENTRY_DEBUG_KEY.strip():
                    raise HTTPException(status_code=404, detail="Not found")
                raise RuntimeError("Sentry backend test")
        else:
            logger.warning("SENTRY_DEBUG_KEY is empty — /health/sentry-test disabled")

    if not settings.is_production:
        @app.get("/test", include_in_schema=False)
        def test_page() -> FileResponse:
            return FileResponse(STATIC_DIR / "test.html")

    return app


app = create_app()
