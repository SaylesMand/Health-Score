# Health Score API

Масштабируемый ML-сервис для оценки риска сердечно-сосудистых заболеваний с системой биллинга и геймификацией.

## Технологический стек

* Язык: Python 3.12+
* Framework: FastAPI
* Database: PostgreSQL + SQLAlchemy 2.0 (Async)
* Migrations: Alembic
* ML: Scikit-learn / CatBoost (Inference)
* Async Tasks: Celery + Redis
* Monitoring: Prometheus + Grafana
* DevOps: Docker (Multi-stage), Docker Compose
* Package Manager: uv

---

## 1. Подготовка (Общий шаг)

Скопируйте пример конфига:
```bash
cp .env.example .env
```
Установите зависимости (для локальной работы):
```bash
uv sync
```

---

## 2. Запуск приложения (Локально)

### 2.1 Инфраструктура
Запустите БД и Redis:
```bash
docker-compose up -d db redis
```

### 2.2 База данных
Накатите миграции и базовые данные:
```bash
uv run alembic upgrade head

# Windows (PowerShell)
$env:PYTHONPATH="."; uv run python scripts/seed_db.py

# Linux/macOS
PYTHONPATH=. uv run python scripts/seed_db.py
```

### 2.3 Запуск сервисов
В разных окнах терминала:
```bash
# API
uv run uvicorn app.main:app --reload

# Worker
uv run celery -A app.tasks.config.celery_app worker --loglevel=info -P solo

# Beat
uv run celery -A app.tasks.config.celery_app beat --loglevel=info
```

---

## 3. Запуск в Docker (Full Stack)

### 3.1 Запуск контейнеров
Запуск всех сервисов (api, frontend, worker, beat, db, redis, prometheus, grafana):
```bash
docker-compose up -d --build
```

UI-дашборд: http://localhost:8501

### 3.2 База данных (Внутри контейнера)
Контейнеры запущены, но база пуста. Выполните миграции внутри запущенного контейнера API:
```bash
docker exec -it health_score_api alembic upgrade head
docker exec -it health_score_api python scripts/seed_db.py
```

API доступно: http://localhost:8000

> Расписание пересчёта уровней лояльности - 1-го числа каждого месяца в 00:00 UTC.
> Для отладочного режима (раз в минуту) выставьте `LOYALTY_RECALC_DEBUG=true` в `.env`.

---

## Основные эндпоинты

* Аутентификация: /api/auth/register, /api/auth/login
* ML Предсказание: /api/predict/predict
* Биллинг: /api/billing/balance, /api/billing/refill
* Геймификация: /api/gamification/generate_challenge, /api/gamification/solve
* Мониторинг:
    * http://localhost:9090 (Prometheus)
    * http://localhost:3000 (Grafana)
