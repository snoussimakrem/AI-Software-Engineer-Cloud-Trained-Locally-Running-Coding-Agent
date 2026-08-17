from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    model_provider: str = "cloud"
    model_base_url: str | None = None
    model_api_key: str | None = None
    cloud_provider: str | None = None
    storage_provider: str = "huggingface"
    hf_token: str | None = None
    app_env: str = "development"
    log_level: str = "INFO"


settings = Settings()
