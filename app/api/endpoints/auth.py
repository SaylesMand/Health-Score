import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import Token, TokenData, UserCreate, UserRead

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    """Регистрация нового пользователя."""
    user_repo = UserRepository(db)

    user_by_email = await user_repo.get_by_email(user_in.email)
    if user_by_email:
        logger.warning(f"Ошибка регистрации: Email {user_in.email} уже занят")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует.",
        )

    user_by_username = await user_repo.get_by_username(user_in.username)
    if user_by_username:
        logger.warning(f"Ошибка регистрации: Имя пользователя {user_in.username} уже занято")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким username уже существует.",
        )

    user = await user_repo.create(user_in)
    logger.info(f"Пользователь успешно зарегистрирован: {user.username}")
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Вход в систему и получение JWT токена."""
    user_repo = UserRepository(db)

    user = await user_repo.get_by_username(form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Ошибка входа для пользователя: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    logger.info(f"Пользователь успешно вошел в систему: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Получение текущего пользователя по JWT токену."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось получить текущего пользователя.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        token_data = TokenData(username=username)
        if token_data.username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception from None

    user_repo = UserRepository(db)
    user = await user_repo.get_by_username(username)
    if user is None:
        raise credentials_exception
    return user


@router.get("/me", response_model=UserRead)
async def get_profile(current_user: Annotated[User, Depends(get_current_user)]):
    """Получение профиля текущего пользователя."""
    return current_user
