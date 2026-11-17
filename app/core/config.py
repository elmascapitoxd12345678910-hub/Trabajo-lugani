"""Configuración global de la aplicación utilizando pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Clase de configuración de la aplicación cargada desde variables de entorno."""

    PROJECT_NAME: str = "E-Commerce API"
    DATABASE_URL: str = "sqlite:///./ecommerce.db"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    SECRET_KEY: str = "supersecret_jwt_key_default_development_key"
    ADMIN_SECRET_KEY: str = "STICKER_ADMIN_2026"
    ALGORITHM: str = "HS256"
    ACCESS_MIN: int = 30
    REFRESH_MIN: int = 10080

    @property
    def origins(self) -> list[str]:
        """Transforma la cadena de CORS_ORIGINS separada por comas en una lista de URLs limpias."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
