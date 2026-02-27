# TaskFlow Backend

TaskFlow is a modular, event-driven task management backend built with FastAPI.

## Stack

- FastAPI + Pydantic v2
- SQLAlchemy 2.0 (async) + Alembic
- PostgreSQL
- Redis
- RabbitMQ
- Celery

## Features

- JWT access tokens + refresh token cookie flow
- Organization and membership management (`OWNER`, `ADMIN`, `MEMBER`)
- Organization-scoped projects
- Organization/project tasks with assignment support
- Notification APIs with read/unread state
- Notification outbox pattern with Celery-based dispatch
- `/health` endpoint checking database, Redis, and RabbitMQ

## Project Layout

```text
app/
  core/            # config, security, logging
  db/              # SQLAlchemy base/session + Alembic migrations
  infra/           # Redis and Celery app wiring
  modules/         # auth, organizations, projects, tasks, notifications, users
  main.py          # FastAPI application entrypoint
tests/
```

## Quick Start (Docker Compose)

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Start services:

```bash
docker compose up --build -d
```

3. Run database migrations:

```bash
docker compose exec api alembic upgrade head
```

4. Open API docs:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

## Local Development (API on Host)

If you run the API on your host machine and only infra in Docker, set hosts in `.env` to `127.0.0.1`:
- `POSTGRES_HOST=127.0.0.1`
- `REDIS_HOST=127.0.0.1`
- `RABBITMQ_HOST=127.0.0.1`

Then:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"

docker compose up -d postgres redis rabbitmq
alembic upgrade head

uvicorn app.main:app --reload
```

Run Celery worker in another shell:

```bash
celery -A app.infra.celery_app.celery_app worker -l INFO
```

## Useful Commands

```bash
# Run tests
pytest

# Lint
ruff check .

# Create a migration
alembic revision --autogenerate -m "your_message"

# Apply migrations
alembic upgrade head
```

## API Surface (High Level)

- `POST /auth/*` - register/login/refresh/logout/me, email verification, password reset
- `GET|POST|PATCH|DELETE /orgs/*` - organizations, membership, invites, ownership transfer
- `GET|POST /orgs/{org_id}/projects` and `GET|PATCH|DELETE /projects/{project_id}`
- `GET|POST /orgs/{org_id}/.../tasks` and `GET|PATCH|DELETE /tasks/{task_id}`
- `GET|PATCH /notifications/*` - list, mark one/all read, unread count

## Background Jobs and Notifications

- Task assignment writes an event into `notification_outbox`.
- A Celery task dispatches outbox rows into user notifications.
- Retry metadata (`attempts`, `next_retry_at`, `last_error`) is stored for failed dispatches.

## Environment Variables

Use `.env.example` as the source of truth. Important variables:

- App: `APP_NAME`, `ENV`, `DEBUG`
- Auth: `JWT_SECRET`, `JWT_ALG`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- Refresh cookie: `REFRESH_TOKEN_DAYS`, `REFRESH_COOKIE_*`
- Database: `POSTGRES_*`
- Redis: `REDIS_*`
- RabbitMQ: `RABBITMQ_*`
- Invite/email token TTLs: `INVITE_TOKEN_TTL_SECONDS`, etc.

## License

MIT (see `LICENSE`).
