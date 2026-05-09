from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.billing import BalanceRead

router = APIRouter()


@router.get("/balance", response_model=BalanceRead)
async def get_balance(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Текущий баланс и уровень лояльности."""
    result = await db.execute(
        select(User).where(User.id == current_user.id).options(selectinload(User.loyalty_level))
    )
    user = result.scalar_one()
    level_name = user.loyalty_level.name if user.loyalty_level else "Bronze"
    return BalanceRead(balance=user.balance, loyalty_level=level_name)
