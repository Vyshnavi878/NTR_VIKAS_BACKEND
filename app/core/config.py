import json
import re
from typing import List, Union
from urllib.parse import quote_plus, unquote
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "NTR Vikasa API"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    DATABASE_URL: str = "mysql+asyncmy://Vyshu:Vyshu%40123@localhost:3306/ntr_vikasa"

    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    UPLOAD_DIR: str = "./uploads"

    # Security & JWT
    JWT_SECRET_KEY: str = "ntr_vikasa_super_secret_jwt_key_2026_district_employment_portal_ap"
    SECRET_KEY: str = "ntr_vikasa_super_secret_jwt_key_2026_district_employment_portal_ap"
    JWT_ALGORITHM: str = "HS256"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Default 60 minutes as per requirements
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # Frontend URL & Email Configuration
    FRONTEND_URL: str = "http://localhost:5173"
    SMTP_HOST: Union[str, None] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Union[str, None] = None
    SMTP_PASSWORD: Union[str, None] = None
    SMTP_FROM_EMAIL: str = "noreply@ntrvikasa.com"
    SMTP_FROM_NAME: str = "NTR Vikasa"
    SMTP_TLS: bool = True

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def sanitize_database_url(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        # Robustly handle passwords with '@' and missing host separator
        m = re.match(r"^(mysql\+asyncmy://)([^:]+):(.+?)(?:@)?(localhost|127\.0\.0\.1)(:\d+)?(/.*)?$", v)
        if m:
            scheme, user, password, host, port, db = m.groups()
            port = port or ":3306"
            db = db or "/ntr_vikasa"
            raw_pwd = unquote(password)
            encoded_pwd = quote_plus(raw_pwd)
            return f"{scheme}{user}:{encoded_pwd}@{host}{port}{db}"
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [v]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
