from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserOut, UserUpdate
from app.services.auth_service import authenticate, create_access_token, decode_token
from app.models.user import User, UserTelegramId
from sqlalchemy import select, delete

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        telegram_ids=[t.telegram_id for t in user.telegram_ids],
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")
    result = await db.execute(
        select(User).options(selectinload(User.telegram_ids)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return _user_to_out(current_user)


@router.patch("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.telegram_ids is not None:
        await db.execute(
            delete(UserTelegramId)
            .where(UserTelegramId.user_id == current_user.id)
            .execution_options(synchronize_session=False)
        )
        for tg_id in payload.telegram_ids:
            db.add(UserTelegramId(user_id=current_user.id, telegram_id=tg_id))
    await db.commit()
    await db.refresh(current_user, attribute_names=["telegram_ids"])
    return _user_to_out(current_user)
