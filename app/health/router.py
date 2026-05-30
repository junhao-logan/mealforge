from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: process is up. No external dependencies touched."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Readiness: can we actually serve traffic (DB reachable)?"""
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
