from fastapi import APIRouter, HTTPException, status

from .. import storage
from ..models import UserInDB, UserRole
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> UserPublic:
    if payload.nickname.lower() in storage.user_by_nickname:
        raise HTTPException(status.HTTP_409_CONFLICT, "Nickname already taken")

    user = UserInDB(
        nickname=payload.nickname,
        role=UserRole(payload.role),
        hashed_password=hash_password(payload.password),
    )
    storage.add_user(user)
    return UserPublic.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user_id = storage.user_by_nickname.get(payload.nickname.lower())
    user = storage.users.get(user_id) if user_id else None
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)
