"""DI для StorageService и FileService."""

from __future__ import annotations

from fastapi import Request

from .config import get_settings
from .services.files import FileService
from .services.storage.base import StorageService
from .services.storage.factory import create_storage_service


def get_storage_service(request: Request) -> StorageService:
    svc = getattr(request.app.state, "storage_service", None)
    if svc is None:
        svc = create_storage_service(get_settings())
        request.app.state.storage_service = svc
    return svc


def get_file_service(request: Request) -> FileService:
    storage_svc = get_storage_service(request)
    return FileService(storage_svc, get_settings())
