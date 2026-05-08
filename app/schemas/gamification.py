import enum

from pydantic import BaseModel, Field


class DifficultyLevel(str, enum.Enum):
    """Сложность задачи."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ChallengeGenerateRequest(BaseModel):
    """Запрос на генерацию задачи."""

    difficulty: DifficultyLevel = Field(..., description="Сложность задачи")


class ChallengeResponse(BaseModel):
    """Ответ на запрос на генерацию задачи."""

    challenge_id: str = Field(..., description="ID задачи")
    question: str = Field(..., description="Текст задачи")
    reward: float = Field(..., description="Награда за выполнение задачи")


class ChallengeSolveRequest(BaseModel):
    """Отправка ответа на задачу."""

    challenge_id: str = Field(..., description="ID задачи")
    answer: str = Field(..., description="Ответ на задачу")


class ChallengeSolveResponse(BaseModel):
    """Ответ на проверку решения задачи."""

    correct: bool = Field(..., description="Верный ли был ответ")
    reward: float = Field(0.0, description="Сумма начисленных кредитов (0, если ответ неверный)")
    message: str = Field(..., description="Человекочитаемое сообщение")
