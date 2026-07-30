from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    # --- Clerk ---
    clerk_issuer: str
    clerk_authorized_parties_raw: str = ""  # 逗号分隔

    @property
    def clerk_jwks_url(self) -> str:
        return f"{self.clerk_issuer.rstrip('/')}/.well-known/jwks.json"

    @property
    def clerk_authorized_parties(self) -> list[str]:
        return [p.strip() for p in self.clerk_authorized_parties_raw.split(",") if p.strip()]


    # --- CORS ---
    cors_allowed_origins_raw: str = "http://127.0.0.1:5173,http://localhost:5173"

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins_raw.split(",") if o.strip()]

    
    # --- Inventory ---
    inventory_expiry_warning_days: int = 3  # 距过期 ≤N 天标记为临期(黄色, I4)

    # --- AI (Anthropic) ---
    # key 可空: mock 测试不需要; 真调用时由 .env 提供
    anthropic_api_key: str = ""
    # 模型串号放配置, 换模型/换档只改这里(不硬编码)
    anthropic_model: str = "claude-haiku-4-5-20251001"
    anthropic_max_tokens: int = 2048   # 单次生成输出上限(一个菜谱够用)

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]