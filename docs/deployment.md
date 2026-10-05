# Сборка, развёртывание и локальный запуск

## Вариант 1. Docker Compose (рекомендуется)

Требования: Docker 24+ с Compose v2, ~1 ГБ свободной памяти.

```bash
cp .env.example .env        # необязательно: значения по умолчанию работают
docker compose up --build
```

| Сервис | Адрес | Что это |
|---|---|---|
| frontend | http://localhost:8080 | Веб-приложение (nginx, проксирует `/api` в backend) |
| backend | http://localhost:8000/api/docs | API + Swagger UI |
| mailpit | http://localhost:8025 | Все письма платформы (коды подтверждения) |
| db | внутренняя сеть | PostgreSQL 16, том `pgdata` |

При старте backend ждёт БД, применяет миграции Alembic и **один раз** заполняет пустую базу демо-данными
(`python -m app.seed --if-empty`). Повторный запуск данные не трогает.

Полезные команды:

```bash
docker compose logs -f backend                                   # логи API
docker compose exec backend python -m app.seed --reset           # пересоздать демо-данные
docker compose exec backend pytest -q                            # тесты внутри контейнера
docker compose down -v                                           # остановить и удалить данные
python scripts/smoke_test.py --base http://localhost:8080        # сквозной smoke-тест по HTTP
```

## Вариант 2. Локально без Docker

Требования: Python 3.12, Node.js 20+. По умолчанию используется SQLite (`backend/fsp_talent.db`),
PostgreSQL не нужен.

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/activate            # Windows;  source .venv/bin/activate — Linux/macOS
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.seed                # демо-данные (можно с --reset)
uvicorn app.main:app --port 8000 --reload

# Frontend (в другом терминале)
cd frontend
npm ci
npm run dev                        # http://127.0.0.1:5173, /api проксируется на :8000
```

Чтобы работать с PostgreSQL локально, задайте
`DATABASE_URL=postgresql+psycopg://fsp:fsp_password@localhost:5432/fsp_talent`.

## Проверки качества

```bash
cd backend && pytest -q && ruff check app tests scripts      # 58 тестов, линтер
cd frontend && npm run typecheck && npm run lint && npm run build
python evaluation/evaluate_tests.py      # валидация механики тестирования (~2 мин)
python evaluation/evaluate_matching.py   # бенчмарк подбора (~30 с)
python evaluation/tune_matching.py       # подбор гиперпараметров (~4 мин)
```

Скрипты оценки не требуют БД и сервера — используют те же модули движков, что и API. Результаты
сохраняются в `evaluation/results/*.md|json`.

## Переменные окружения

Полный список с комментариями — в [`.env.example`](../.env.example). Основные:

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `DATABASE_URL` | SQLite в `backend/` | Строка подключения SQLAlchemy |
| `JWT_SECRET` | dev-значение | **Обязательно сменить в продакшене** |
| `EMAIL_DEV_EXPOSE_CODE` | `true` | Демо-режим: код подтверждения виден в UI. В продакшене — `false` |
| `SMTP_HOST` / `SMTP_PORT` | — / 1025 | SMTP (в compose — Mailpit) |
| `TEST_LENGTH`, `TEST_TIME_LIMIT_MINUTES` | 20, 30 | Параметры теста |
| `RETAKE_COOLDOWN_DAYS`, `GRADE_CHANGE_COOLDOWN_DAYS` | 30, 90 | Кулдауны |
| `FSP_REGISTRY_MODE`, `FSP_REGISTRY_URL` | `mock` | Источник данных ФСП: `mock` или `http` |
| `MATCHING_WEIGHTS_JSON` | — | Переопределение весов матчинга |
| `INVITATIONS_DAILY_LIMIT` | 40 | Анти-спам лимит приглашений |

## Развёртывание на сервере

Достаточно одной ВМ (2 vCPU / 2 ГБ): `docker compose up -d --build`, затем поставить перед портом 8080
TLS-терминатор (nginx/Caddy/Traefik) и закрыть внешний доступ к 8000/8025. Перед публичным
запуском: `JWT_SECRET`, `POSTGRES_PASSWORD`, `EMAIL_DEV_EXPOSE_CODE=false`, реальный SMTP.

## Типовые проблемы

* **Порт занят** (8000/8080/8025) — измените публикацию портов в `docker-compose.yml`.
* **Vite не открывается по `localhost`** на Windows — используйте `http://127.0.0.1:5173`
  (dev-сервер слушает IPv4).
* **Пустая выдача у работодателя** — кандидат попадает в подборки только после подтверждённой
  категории и согласия на публикацию профиля (Настройки → «Публикация профиля»).
