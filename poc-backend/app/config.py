from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Azure AI Foundry
    ai_foundry_endpoint: str = ""
    ai_foundry_key: str = ""
    ai_model: str = "mistral-large-latest"
    ai_temperature: float = 0.3
    ai_max_tokens: int = 4000

    # Cosmos DB (MongoDB API)
    cosmos_connection: str = ""
    cosmos_database: str = "agentize-poc-db"

    # Blob Storage
    blob_connection: str = ""
    blob_container: str = "pdf-output"

    # Key Vault (optional — secrets are typically injected via Container App env refs)
    key_vault_url: str = ""

    # Bot Framework
    bot_app_id: str = ""
    bot_app_password: str = ""

    # Telegram (optional)
    telegram_bot_token: str = ""

    # Application Insights
    applicationinsights_connection_string: str = ""

    # App
    environment: str = "poc"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
