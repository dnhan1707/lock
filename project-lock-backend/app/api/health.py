from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
    # Connection failures can surface as raw OSError (e.g. DNS or refused connection), not SQLAlchemyError.
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc
    return {"status": "ok", "database": "ok"}
