from functools import lru_cache
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 480

    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "nexus-exchange-files"
    R2_ENDPOINT_URL: str = ""
    R2_PUBLIC_DOMAIN: str = ""

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash-preview-05-20"

    ADMIN_USERNAME: str = Field("admin", validation_alias=AliasChoices("ADMIN_USERNAME", "ADMIN_USER", "ADMIN_LOGIN"))
    ADMIN_PASSWORD: str = Field("admin123secure", validation_alias=AliasChoices("ADMIN_PASSWORD", "ADMIN_PASS", "ADMIN_SECRET"))
    ADMIN_EMAIL: str = ""

    SMTP_HOST: str = "smtpout.secureserver.net"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_SECURE: bool = False
    SMTP_SENDER_NAME: str = "Nexus Exchange"
    CONTACT_TO_EMAIL: str = ""
    SITE_URL: str = "http://localhost:8000"

    APP_ENV: str = "development"
    FRONTEND_DIST_PATH: str = "./static"

    CORS_ALLOWED_ORIGINS: str = "http://localhost:4200,http://localhost:3000"
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_REQUESTS: int = 120
    WS_MAX_CONNECTIONS_PER_IP: int = 5
    WS_MAX_CONNECTIONS_TOTAL: int = 500
    MAX_UPLOAD_SIZE_MB: int = 15

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @field_validator("ADMIN_USERNAME", "ADMIN_PASSWORD", mode="before")
    @classmethod
    def strip_admin_env_values(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
