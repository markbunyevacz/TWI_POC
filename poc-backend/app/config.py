from pydantic_settings import BaseSettings


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

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
