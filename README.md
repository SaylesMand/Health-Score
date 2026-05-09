# Health Score API

Асинхронный ML-сервис: оценка вероятности сердечно-сосудистых заболеваний по биометрии. С биллингом, ролями, геймификацией и атомарной защитой средств.

- УТП и финмодель: [BUSINESS_PLAN.md](BUSINESS_PLAN.md).
- Обзор работоспособности сервиса: [Google Drive](https://drive.google.com/file/d/1LKkeDTBA9JWumtD3ZXs0GdSNza6OtPLM/view?usp=sharing)

## Структура проекта

```
.
├── app/                     # Backend (FastAPI)
│   ├── api/                 # Эндпоинты и зависимости (auth, predict, billing, gamification, admin)
│   ├── core/                # Конфиг, БД, security
│   ├── models/              # SQLAlchemy-модели
│   ├── schemas/             # Pydantic-схемы
│   ├── repositories/        # Доступ к БД
│   ├── services/            # Бизнес-логика (биллинг)
│   ├── ml/                  # Загрузка ML-моделей
│   ├── tasks/               # Celery: воркер, beat, watchdog
│   └── main.py              # Точка входа FastAPI
├── frontend/                # Streamlit UI (auth, billing, predict, gamification, admin)
├── alembic/                 # Миграции
├── tests/                   # pytest + testcontainers + fakeredis
├── scripts/                 # seed_db и утилиты
├── grafana/                 # Provisioning datasource и дашборда
├── docker-compose.yaml
├── Dockerfile
├── entrypoint.sh            # Миграции + seed + старт api
└── pyproject.toml
```

## Стек

Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), asyncpg, PostgreSQL 17, Alembic, Celery 5, Redis 7, scikit-learn, XGBoost, Streamlit, Prometheus, Grafana, Docker Compose, uv, pytest.

## Подготовка

Нужны Docker Desktop и Git. Для локального запуска без Docker - ещё [uv](https://docs.astral.sh/uv/).

```bash
git clone <url>
cd Health-Score
cp .env.example .env
```

В `.env` обязательны: `POSTGRES_*`, `SECRET_KEY` (16+ символов). Для автосоздания админа - `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.

## Запуск через Docker

```bash
docker compose up -d --build
```

Контейнер `api` сам накатывает миграции и сидирует данные. После старта:

| Сервис     | URL                            | Логин          |
|------------|--------------------------------|----------------|
| Swagger    | http://localhost:8000/docs     | -              |
| Streamlit  | http://localhost:8501          | свой / админ   |
| Prometheus | http://localhost:9090          | -              |
| Grafana    | http://localhost:3000          | admin / admin  |

Полная очистка (с данными БД): `docker compose down -v`.

## Локальный запуск

```bash
docker compose up -d db redis
uv sync --all-groups
uv run alembic upgrade head
PYTHONPATH=. uv run python scripts/seed_db.py    # PowerShell: $env:PYTHONPATH="."; uv run python scripts/seed_db.py
```

В трёх терминалах:

```bash
uv run uvicorn app.main:app --reload
uv run celery -A app.tasks.config.celery_app worker --loglevel=info -P solo
uv run celery -A app.tasks.config.celery_app beat --loglevel=info
```

UI отдельно: `uv run streamlit run frontend/main.py`.

## Эндпоинты

| Метод | Путь                                  | Назначение                              |
|-------|---------------------------------------|-----------------------------------------|
| POST  | /api/auth/register                    | Регистрация (welcome-бонус 200 кр)      |
| POST  | /api/auth/login                       | Логин, выдача JWT                       |
| GET   | /api/auth/me                          | Профиль                                 |
| GET   | /api/billing/balance                  | Баланс и уровень лояльности             |
| POST  | /api/predict/predict                  | Заказать ML-предсказание                |
| GET   | /api/predict/history                  | История предсказаний                    |
| POST  | /api/gamification/generate_challenge  | Получить математическую задачу          |
| POST  | /api/gamification/solve               | Сдать ответ, получить бонус             |
| GET   | /api/admin/users                      | (admin) Список пользователей            |
| POST  | /api/admin/users/{id}/refill          | (admin) Принудительное пополнение       |

Полные схемы - в Swagger.

## Тесты

```bash
uv run pytest
```

testcontainers поднимает Postgres на сессию, fakeredis заменяет Redis, Celery `delay()` подменяется на синхронный вызов в `ThreadPoolExecutor`. Порог покрытия 70 процентов зашит в `pyproject.toml`.

Что покрывают тесты:

- `test_auth_api.py` - регистрация, дубликаты, логин, `/me`, JWT.
- `test_billing_api.py`, `test_billing_service.py` - чарж, refund, refill, скидки, FOR UPDATE.
- `test_predict_api.py` - списание + постановка задачи, 402, история, гейтинг тарифов.
- `test_gamification_api.py` - задачи, проверка ответа, лимит 20/час, защита от двойного начисления.
- `test_admin_api.py` - `require_admin`, список пользователей, refill.
- `test_loyalty_worker.py` - пересчёт уровней по тратам за 30 дней.
- `test_schemas.py`, `test_security.py` - Pydantic-валидация, хеш пароля, JWT.

Итог: **54 теста, покрытие 75.77%** (порог 70%).
