from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "development"
    supabase_url: str = "http://127.0.0.1:54321"
    supabase_publishable_key: str = ""
    supabase_auth_url: str = ""
    supabase_rest_url: str = ""
    jwt_issuer: str = ""
    jwt_audience: str = "authenticated"
    jwt_algorithms: list[str] = ["ES256", "RS256"]
    jwt_secret: str = ""
    database_url: str = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    redis_url: str = "redis://127.0.0.1:6379/0"
    cors_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]
    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini-2025-04-14"
    openai_api_key: str = ""
    llm_timeout: float = Field(default=30, ge=1, le=120)
    llm_max_output_tokens: int = Field(default=2200, ge=100, le=8000)
    max_attempts: int = Field(default=3, ge=1, le=5)
    job_deadline: int = Field(default=180, ge=30, le=900)
    lease_seconds: int = Field(default=240, ge=30)
    worker_concurrency: int = Field(default=2, ge=1, le=10)
    verify_session: bool = True

    @model_validator(mode="after")
    def secure(self):
        if self.environment == "production":
            if self.llm_provider != "openai" or not self.openai_api_key:
                raise ValueError("Production requires an explicitly configured LLM provider key.")
            if not self.supabase_url.startswith("https://") or not self.verify_session:
                raise ValueError("Production requires HTTPS Supabase and session validation.")
            if any(not origin.startswith("https://") for origin in self.cors_origins):
                raise ValueError("Production requires HTTPS origins.")
        if self.lease_seconds <= self.job_deadline:
            raise ValueError("Lease must exceed the overall job deadline.")
        return self

    @property
    def auth_url(self) -> str:
        return self.supabase_auth_url or self.supabase_url.rstrip("/") + "/auth/v1"

    @property
    def rest_url(self) -> str:
        return self.supabase_rest_url or self.supabase_url.rstrip("/") + "/rest/v1"

    @property
    def issuer(self) -> str:
        return self.jwt_issuer or self.supabase_url.rstrip("/") + "/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
