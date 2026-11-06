# Project Lock Backend

FastAPI + SQLAlchemy (async) + PostgreSQL + Alembic, run with Docker.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose), and it must be running.
- Git.

You do not need Python or PostgreSQL installed on your machine to run the backend with Docker.

## Quick start (Docker)

```bash
cd project-lock-backend

# 1. Create your local env file (never commit it)
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env

# 2. Build and start the database, migrations, and API
docker compose up --build

# 3. In another terminal, seed sample data (optional)
docker compose run --rm api python -m seeds
```

Once it is running:

| What              | URL                                  |
| ----------------- | ------------------------------------ |
| API               | http://localhost:8000                |
| Health check      | http://localhost:8000/health         |
| Interactive docs  | http://localhost:8000/docs           |
| PostgreSQL        | `localhost:5432` (user/db from `.env`) |

`/health` returns `{"status": "ok", "database": "ok"}` when the API can reach the database. It returns `503` otherwise.

Stop everything with `docker compose down`. To wipe the database volume and start fresh, run `docker compose down -v`.

## What happens on `docker compose up`

1. `db` starts PostgreSQL 17 and waits until it is healthy.
2. `migrate` runs `alembic upgrade head` and exits. If it fails, the API does not start.
3. `api` starts uvicorn with `--reload`, so code changes apply without a rebuild.

## Database migrations (Alembic)

Schema changes are made with migrations. Do not create or alter tables by hand.

### Adding or changing a model

1. Add or edit the model in `app/db/models/` (one module per model or group of related models).
2. Import the module in [app/db/models/__init__.py](app/db/models/__init__.py). Alembic only sees models that are imported there.
3. Generate a migration. Review the generated file in `alembic/versions/`, because autogenerate does not catch everything (for example, renamed columns).

   ```bash
   docker compose run --rm api alembic revision --autogenerate -m "describe the change"
   ```

4. Apply it:

   ```bash
   docker compose run --rm api alembic upgrade head
   ```

Other useful commands:

```bash
docker compose run --rm api alembic current     # show the revision the database is on
docker compose run --rm api alembic history     # list all revisions
docker compose run --rm api alembic downgrade -1  # undo the last migration
```

Commit the migration files in `alembic/versions/` together with the model changes.

## Seeding data

Seeders insert sample or required reference data so everyone's local database matches.

```bash
docker compose run --rm api python -m seeds
```

- Seeders live in `seeds/seeders/`. Each is a subclass of `Seeder` (see [seeds/base.py](seeds/base.py)).
- Register each seeder in the `SEEDERS` list in [seeds/seeders/__init__.py](seeds/seeders/__init__.py), with parents before children.
- `run()` must be **idempotent**: running the seed command twice must not duplicate rows. Check whether the row exists, or use an upsert.
- All seeders run in one transaction. If one fails, nothing is written.
- Seeding is refused when `APP_ENV=production`.

Example seeder:

```python
# seeds/seeders/users.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User  # your model
from seeds.base import Seeder


class UserSeeder(Seeder):
    async def run(self, session: AsyncSession) -> None:
        existing = await session.scalar(select(User).where(User.email == "demo@example.com"))
        if existing is None:
            session.add(User(email="demo@example.com"))
```

Then add `UserSeeder` to `SEEDERS` in `seeds/seeders/__init__.py`.

## Running without Docker (optional)

Use this if you want to run Python directly on your machine. Python 3.13 is recommended.

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d db           # only the database runs in Docker
alembic upgrade head
uvicorn app.main:app --reload
python -m seeds
```

Run these from `project-lock-backend/`. Local runs read `DATABASE_URL` from `.env`.

## Project structure

```
project-lock-backend/
├── app/                      # FastAPI application
│   ├── main.py               # app instance and lifespan hooks
│   ├── api/                  # HTTP routes
│   │   ├── router.py         # aggregates all routers; add new routers here
│   │   └── health.py         # GET /health
│   ├── core/
│   │   └── config.py         # settings loaded from environment / .env
│   └── db/
│       ├── base.py           # SQLAlchemy declarative Base
│       ├── session.py        # async engine and get_db() dependency
│       └── models/           # ORM models (imported in models/__init__.py)
├── alembic/                  # migrations
│   ├── env.py                # Alembic config (async, uses DATABASE_URL)
│   └── versions/             # generated migration files (commit these)
├── seeds/                    # seed data
│   ├── __main__.py           # entry point: python -m seeds
│   ├── base.py               # Seeder base class
│   └── seeders/              # one module per seeder; register in __init__.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt          # pinned dependencies
├── alembic.ini
├── .env.example              # copy to .env
└── README.md
```

## Adding a new dependency

1. Install it locally and pin the exact version in `requirements.txt`.
2. Rebuild the image so the team gets it: `docker compose build`.

## Troubleshooting

- **`port is already allocated` on 5432 or 8000.** Another program uses the port. Change `POSTGRES_PORT` or `API_PORT` in `.env`. For a local run, also update the port in `DATABASE_URL`.
- **`/health` returns 503 or the API logs show connection errors.** Check `docker compose ps`. `db` should show `healthy`. If it does not, run `docker compose logs db`.
- **`migrate` exits with an error.** Run `docker compose logs migrate`. The database may be on an older revision than your code, or a migration may be broken.
- **I changed `.env` and nothing changed.** Restart with `docker compose up -d`. Compose reads `.env` at startup.
- **Start over with a clean database.** Run `docker compose down -v`, then `docker compose up --build` and seed again.
- **Docker is not running.** Start Docker Desktop and wait until it reports that it is running.
