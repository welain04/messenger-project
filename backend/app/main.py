from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import get_settings
from .middleware import JWTUserMiddleware
from .routers import auth, chats, messages, notifications, users

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Online School Messenger API",
        version="1.0.0",
        description="In-memory messenger backend for an online school.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(JWTUserMiddleware)

    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(auth.router)
    api_v1.include_router(users.router)
    api_v1.include_router(chats.router)
    api_v1.include_router(messages.router)
    api_v1.include_router(notifications.router)
    app.include_router(api_v1)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/test", include_in_schema=False)
    def test_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "test.html")

    return app


app = create_app()
