import logging
from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.permissions import require_admin
from app.core.database import get_db
from app.repositories.user import UserRepository
from app.schemas.billing import RefillRequest, RefillResponse
from app.schemas.user import UserRead
from app.services.billing import BillingService

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/users", response_model=Sequence[UserRead])
async def list_users(db: Annotated[AsyncSession, Depends(get_db)]):
    """Возвращает список всех пользователей."""
    return await UserRepository(db).list_all()


@router.post("/users/{user_id}/refill", response_model=RefillResponse)
async def admin_refill(
    user_id: int,
    refill: RefillRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Принудительно пополняет баланс выбранного пользователя."""
    target = await UserRepository(db).get_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")
    new_balance = await BillingService(db).refill(user_id, refill.amount)
    logger.info(f"Admin refill: user_id={user_id}, сумма={refill.amount}")
    return RefillResponse(message="Баланс пополнен админом.", new_balance=new_balance)
