from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.modules.users.models import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, MeResponse
from app.modules.auth.service import AuthService
from app.modules.auth.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
service = AuthService()


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    max_age = settings.refresh_token_days * 24 * 60 * 60
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path=settings.refresh_cookie_path,
        max_age=max_age,
    )


def _delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
    )

@router.post("/register", response_model=TokenResponse)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db_session)) -> TokenResponse:
    token = await service.register(db, payload.email, payload.username, payload.password)
    return TokenResponse(access_token=token)

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db_session)) -> TokenResponse:
    user = await service.login(db, payload.email, payload.password)

    access = await service.issue_access_token(str(user.id))
    refresh = await service.create_refresh_session(str(user.id))

    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response) -> TokenResponse:
    raw = request.cookies.get(settings.refresh_cookie_name)
    if not raw:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    new_refresh, user_id = await service.rotate_refresh_session(raw)

    access = await service.issue_access_token(user_id)
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=access)


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict:
    raw = request.cookies.get(settings.refresh_cookie_name)
    if raw:
        await service.revoke_refresh_session(raw)
    _delete_refresh_cookie(response)
    return {"status": "ok"}

@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        is_superuser=current_user.is_superuser,
    )