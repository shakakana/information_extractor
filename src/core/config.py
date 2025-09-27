"""Configuration settings for the application."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "" # Your project name
    
    # LLM Settings
    MODEL: str
    UDAL_PAT: str
    BASE_URL: str
    LLM_CHAT_ENDPOINT: str
    LLM_BATCH_ENDPOINT: str

    # Teradata Database Settings
    TERADATA_HOST: str
    TERADATA_USER: str
    TERADATA_PASSWORD: str
    TERADATA_DATABASE: str

    # MSSQL Database Settings
    MSSQL_SERVER: str
    MSSQL_DATABASE: str
    MSSQL_USER: str
    MSSQL_PASSWORD: str
    MSSQL_DRIVER: str

    # Oracle Database Settings
    ORACLE_USER: str
    ORACLE_PASSWORD: str
    ORACLE_DSN: str
    
    model_config = SettingsConfigDict(
        env_file = [".env", ".env.local"], env_file_encoding="utf-8", case_sensitive=True
    )
    

@lru_cache
def get_settings():
    return Settings()


# Instantiate settings object for project access
settings = get_settings()

    