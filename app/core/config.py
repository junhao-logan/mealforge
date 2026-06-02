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

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
