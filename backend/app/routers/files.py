from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from ..deps import require_verified_email
from ..deps_storage import get_file_service, get_storage_service
from ..models import UserInDB
from ..schemas import SignedUrlOut
from ..services.files import FileService
from ..services.storage.base import StorageService
from ..services.storage.local import LocalFilesystemStorage

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/avatars/{user_id}", response_model=SignedUrlOut | None)
def get_avatar_url(
    user_id: UUID,
    current: UserInDB = Depends(require_verified_email),
    files: FileService = Depends(get_file_service),
) -> SignedUrlOut | None:
    signed = files.get_avatar_signed_url(user_id, current)
    if signed is None:
        return None
    return SignedUrlOut(url=signed.url, expires_at=signed.expires_at, storage_key=signed.storage_key)


@router.get("/serve")
def serve_local_file(
    key: str = Query(..., min_length=1),
    exp: int = Query(...),
    sig: str = Query(..., min_length=1),
    filename: str | None = Query(default=None),
    files: FileService = Depends(get_file_service),
    storage_svc: StorageService = Depends(get_storage_service),
) -> Response:
    """Proxy для local-провайдера (presigned URL с HMAC)."""
    if not isinstance(storage_svc, LocalFilesystemStorage):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if not files.verify_local_serve_token(key, exp, sig):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ссылка недействительна или истекла")
    try:
        data, content_type = storage_svc.read_object(key)
    except Exception:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Файл не найден") from None
    headers = {}
    if filename:
        headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return Response(content=data, media_type=content_type, headers=headers)
