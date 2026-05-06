from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str

    RATE_LIMIT_CREATE_PAYMENT: str
    RATE_LIMIT_GET_PAYMENT: str
    RATE_LIMIT_REFUND: str

    SENTRY_KEY: str


def get_settings() -> Settings:
    return Settings()


settings = get_settings()