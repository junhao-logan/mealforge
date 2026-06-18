from fastapi import FastAPI

from app.core.config import get_settings
from app.health.router import router as health_router
from app.users.router import router as users_router   
from app.ingredients.router import router as ingredients_router   
from app.recipes.router import router as recipes_router   
from app.nutrition.router import router as nutrition_router  

settings = get_settings()

app = FastAPI(title="MealForge API", version="0.1.0")

app.include_router(health_router)
app.include_router(users_router)                       
app.include_router(ingredients_router)                              
app.include_router(recipes_router)                          
app.include_router(nutrition_router)                           



@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "MealForge API", "env": settings.app_env}
