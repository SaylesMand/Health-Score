import logging
import secrets
import uuid
from typing import Annotated

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.transaction import TransactionType
from app.models.user import User
from app.repositories.transaction import TransactionRepository
from app.schemas.gamification import (
    ChallengeGenerateRequest,
    ChallengeResponse,
    ChallengeSolveRequest,
    ChallengeSolveResponse,
    DifficultyLevel,
)

logger = logging.getLogger(__name__)

router = APIRouter()

redis_client = redis.from_url(
    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1", decode_responses=True
)

_CHALLENGE_TTL_SECONDS = 300
_HOURLY_LIMIT = 20
_HOURLY_WINDOW_SECONDS = 3600


def _build_challenge(diff: DifficultyLevel) -> tuple[str, str, float]:
    if diff == DifficultyLevel.EASY:
        a, b = secrets.randbelow(90) + 10, secrets.randbelow(90) + 10
        op = "+" if secrets.choice([True, False]) else "-"
        return f"Решите: {a} {op} {b} = ?", str(a + b if op == "+" else a - b), 10.0

    if diff == DifficultyLevel.MEDIUM:
        x = secrets.randbelow(15) + 2
        a = secrets.randbelow(8) + 2
        b = secrets.randbelow(20) + 1
        c = a * x + b
        return f"Решите уравнение для x: {a}x + {b} = {c}", str(x), 30.0

    if diff == DifficultyLevel.HARD:
        a = secrets.choice([2, 4, 6, 8, 10])
        b = secrets.randbelow(5) + 2
        ans = (a // 2) * (b**2)
        return (
            f"Вычислите определённый интеграл функции {a}x dx на отрезке от 0 до {b}:",
            str(ans),
            50.0,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Неизвестный уровень сложности."
    )


@router.post("/generate_challenge", response_model=ChallengeResponse)
async def generate_challenge(
    request: ChallengeGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Генерирует математическую задачу для заработка кредитов."""
    rate_key = f"challenge_rate:{current_user.id}"
    used = await redis_client.incr(rate_key)
    if used == 1:
        await redis_client.expire(rate_key, _HOURLY_WINDOW_SECONDS)
    if used > _HOURLY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Лимит {_HOURLY_LIMIT} задач/час исчерпан. Попробуйте позже.",
        )

    question, answer, reward = _build_challenge(request.difficulty)
    challenge_id = str(uuid.uuid4())
    await redis_client.setex(
        f"challenge:{current_user.id}:{challenge_id}",
        _CHALLENGE_TTL_SECONDS,
        f"{answer}|{reward}",
    )

    logger.info(
        f"Задача {challenge_id} ({request.difficulty.value}) "
        f"сгенерирована для user={current_user.id}"
    )
    return ChallengeResponse(challenge_id=challenge_id, question=question, reward=reward)


@router.post("/solve", response_model=ChallengeSolveResponse)
async def solve_challenge(
    request: ChallengeSolveRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChallengeSolveResponse:
    """Проверяет ответ и начисляет кредиты."""
    key = f"challenge:{current_user.id}:{request.challenge_id}"
    stored = await redis_client.get(key)
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Задача не найдена или время вышло.",
        )

    correct_answer, reward_str = stored.split("|", 1)
    if request.answer.strip().lower() != correct_answer.lower():
        logger.info(f"Неверный ответ от user={current_user.id} на {request.challenge_id}")
        return ChallengeSolveResponse(correct=False, reward=0.0, message="Неверный ответ.")

    if not await redis_client.delete(key):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Задача уже была решена.",
        )

    reward = float(reward_str)
    user = await db.get(User, current_user.id, with_for_update=True)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")
    user.balance += reward
    TransactionRepository(db).add(user_id=user.id, amount=reward, t_type=TransactionType.REFILL)
    await db.commit()

    logger.info(f"User={user.id} решил {request.challenge_id}, награда={reward}")
    return ChallengeSolveResponse(
        correct=True,
        reward=reward,
        message=f"Ответ верный! Вам начислено {reward} кредитов.",
    )
