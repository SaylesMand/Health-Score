from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models.transaction import TransactionType
from app.models.user import User
from app.repositories.transaction import TransactionRepository
from app.schemas.billing import RefillRequest, RefillResponse

router = APIRouter()


@router.post("/refill", response_model=RefillResponse)
async def refill_balance(
    refill_data: RefillRequest,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Пополнение баланса пользователя."""
    transaction_repo = TransactionRepository(db)

    await transaction_repo.create(
        user_id=current_user.id,
        amount=refill_data.amount,
        t_type=TransactionType.REFILL,
    )

    await db.refresh(current_user)

    return RefillResponse(
        message="Баланс успешно пополнен.",
        new_balance=current_user.balance,
    )
