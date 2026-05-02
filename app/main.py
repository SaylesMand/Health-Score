from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.endpoints import auth, billing, predict
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="API для оценки риска сердечно-сосудистых заболеваний с биллингом.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Аутентификация"])
app.include_router(predict.router, prefix="/api/predict", tags=["Предсказание"])
app.include_router(billing.router, prefix="/api/billing", tags=["Биллинг"])

Instrumentator().instrument(app).expose(app)


@app.get("/health", tags=["Системные"])
async def health_check():
    """Проверка работоспособности сервера."""
    return {"status": "ok"}
