from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator, Field, SecretStr
from urllib.parse import urlsplit
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "local"
    database_url: str = ""
    app_secret: str = ""
    public_base_url: str = ""
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    cookie_secure: bool = False
    session_ttl_minutes: int = 480
    demo_quick_login: bool = False
    geoblock_enabled: bool = False
    geoblock_deny_countries: str = "KG"
    geoip_db_path: str = "runtime-data/country.mmdb"
    trusted_proxy_cidrs: str = ""
    frontend_dist: str = str(Path(__file__).resolve().parents[2] / "frontend" / "dist")
    port: int = 8000
    organizer_name: str = Field(default="Организатор учебного проекта B bank", max_length=160)
    ai_enabled: bool = False
    ai_api_key: SecretStr = SecretStr("")
    ai_api_format: Literal["openai_chat", "openai_responses", "anthropic", "gemini"] = "openai_chat"
    ai_api_base_url: str = ""
    ai_model: str = Field(default="", max_length=100)
    ai_provider_label: str = Field(default="", max_length=120)
    ai_timeout_seconds: float = Field(default=15, ge=1, le=18)
    ai_max_output_tokens: int = Field(default=600, ge=128, le=8192)
    ai_token_parameter: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    ai_json_mode: bool = True
    ai_hourly_limit: int = Field(default=20, ge=1, le=200)
    ai_daily_budget_requests: int = Field(default=200, ge=1, le=10000)
    support_phone_primary: str = Field(default="996220715205", pattern=r"^[1-9][0-9]{7,14}$")
    support_phone_secondary: str = Field(default="996995393911", pattern=r"^[1-9][0-9]{7,14}$")

    @model_validator(mode="after")
    def verify(self):
        if not self.database_url:
            raise ValueError("Укажите DATABASE_URL PostgreSQL")
        if len(self.app_secret) < 32:
            raise ValueError("APP_SECRET должен содержать минимум 32 символа")
        if not self.ai_api_base_url:
            self.ai_api_base_url = {"openai_chat": "https://api.openai.com/v1", "openai_responses": "https://api.openai.com/v1", "anthropic": "https://api.anthropic.com/v1", "gemini": "https://generativelanguage.googleapis.com/v1beta"}[self.ai_api_format]
        endpoint = urlsplit(self.ai_api_base_url)
        if endpoint.scheme != "https" or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
            raise ValueError("AI_API_BASE_URL должен быть HTTPS-адресом API без пароля и параметров")
        if not self.ai_provider_label:
            self.ai_provider_label = {"api.openai.com": "OpenAI", "api.anthropic.com": "Anthropic Claude", "generativelanguage.googleapis.com": "Google Gemini", "openrouter.ai": "OpenRouter"}.get(endpoint.hostname, endpoint.hostname)
        if self.ai_enabled and (not self.ai_api_key.get_secret_value() or not self.ai_model):
            raise ValueError("Для AI_ENABLED=true задайте AI_API_KEY и AI_MODEL")
        if self.app_env == "production":
            if not self.cookie_secure or not self.public_base_url.startswith("https://"):
                raise ValueError("В production нужны COOKIE_SECURE=true и PUBLIC_BASE_URL с HTTPS")
            if self.demo_quick_login:
                raise ValueError("Быстрый демовход запрещён в production")
        return self


@lru_cache
def settings():
    return Settings()
