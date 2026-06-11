from fastapi import APIRouter, HTTPException, status

from .. import storage
from ..models import UserInDB, UserRole
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> UserPublic:
    if storage.get_user_by_nickname(payload.nickname) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Этот никнейм уже занят")

    user = UserInDB(
        nickname=payload.nickname,
        role=UserRole(payload.role),
        hashed_password=hash_password(payload.password),
    )
    storage.create_user(user)
    return UserPublic.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = storage.get_user_by_nickname(payload.nickname)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный никнейм или пароль")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)
