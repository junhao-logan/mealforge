from fastapi import FastAPI

from app.core.config import get_settings
from app.health.router import router as health_router

settings = get_settings()

app = FastAPI(title="MealForge API", version="0.1.0")

app.include_router(health_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "MealForge API", "env": settings.app_env}
