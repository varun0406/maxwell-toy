from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./maxwell_acc.db"
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    APP_NAME: str = "Maxwell Accounting"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
