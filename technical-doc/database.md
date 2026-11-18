# What database:
- Postgres + SQLAlchemy

Conventions: PostgreSQL 17, SQLAlchemy 2 async models in `app/db/models/`, migrations with Alembic (see the backend README).

# Schema design

Status: **design only**. Tables are marked with the phase that creates them. Each phase ships its own Alembic migration.
