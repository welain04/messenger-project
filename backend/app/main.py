from pathlib import Path
import logging

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import db
from .config import get_settings
from .errors import validation_exception_handler
from .middleware import JWTUserMiddleware
from .routers import admin, auth, chats, files, messages, notifications, uploads, users
from .services.storage.factory import create_storage_service

logger = logging.getLogger("messenger")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    db.init_db()
    app = FastAPI(
        title="Online School Messenger API",
        version="1.0.0",
        description="Messenger backend for an online school.",
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
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(JWTUserMiddleware)
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

    @app.get("/test", include_in_schema=False)
    def test_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "test.html")

    return app


app = create_app()
