from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings


class Environment(StrEnum):
    DEV = "development"
    STAGING = "staging"
    PROD = "production"


class Settings(BaseSettings):
    APP_NAME: str = Field(default="ScienceBot WhatsApp API")
    APP_VERSION: str = Field(default="1.0.0")
    ENVIRONMENT: Environment = Field(default=Environment.DEV)

    # Evolution API Configuration
    EVOLUTION_API_URL: str = Field(default="http://localhost:8080")
    EVOLUTION_API_KEY: str = Field(default="mi_api_key_evolution")

    # Webhook Configuration
    WEBHOOK_EVENTS: list[str] = Field(
        default_factory=lambda: [
            "MESSAGES_UPSERT",
            "MESSAGES_UPDATE",
            "SEND_MESSAGE",
        ],
        description="Events to listen to",
    )

    # Bot Configuration
    BOT_NAME: str = Field(default="ScienceBot")

    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    OPENAI_MAX_TOKENS: int = Field(default=1000)
    OPENAI_TEMPERATURE: float = Field(default=0)

    # MongoDB Atlas Configuration
    MONGO_URL: str = Field(default="mongodb://localhost:27017")
    MONGO_DATABASE: str = Field(default="ScienceBot")
    MONGO_DOCUMENTS_COLLECTION: str = Field(default="Documents")
    MONGO_PAGES_COLLECTION: str = Field(default="ScienceBot")

    # Security
    LOGFIRE_TOKEN: str | None = Field(default=None)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
        "frozen": True,
    }


settings = Settings()  # type: ignore
