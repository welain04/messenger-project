from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from ..deps import require_verified_email
from ..deps_storage import get_file_service
from ..models import UserInDB
from ..schemas import StagedUploadOut
from ..services.files import FileService

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=StagedUploadOut, status_code=status.HTTP_201_CREATED)
async def stage_upload(
    file: UploadFile = File(...),
    current: UserInDB = Depends(require_verified_email),
    files: FileService = Depends(get_file_service),
) -> StagedUploadOut:
    staged = files.stage_upload(current, file)
    return StagedUploadOut.model_validate(staged)


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_upload(
    upload_id: UUID,
    current: UserInDB = Depends(require_verified_email),
    files: FileService = Depends(get_file_service),
) -> None:
    files.cancel_staged_upload(upload_id, current)
