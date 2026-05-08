from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status

from app.api.endpoints.auth import get_current_user
from app.models.user import User, UserRole


def require_role(*allowed: UserRole) -> Callable:
    """Зависимость FastAPI: пропускает пользователей только с указанными ролями."""

    async def _check(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции.",
            )
        return current_user

    return _check


require_admin = require_role(UserRole.ADMIN)
