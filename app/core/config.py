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
    OPENAI_EMBEDDING_DIMENSIONS: int = Field(default=1536)
    OPENAI_MAX_TOKENS: int = Field(default=1000)
    OPENAI_TEMPERATURE: float = Field(default=0)

    # LlamaCloud OCR Configuration
    LLAMA_CLOUD_API_KEY: str = Field(default="")

    # Document Chunking Configuration
    CHUNK_SIZE_TOKENS: int = Field(default=1000)
    CHUNK_OVERLAP_TOKENS: int = Field(default=100)

    # PostgreSQL Configuration (NEW)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/sciencebot"
    )

    # Conversation Configuration
    CONVERSATION_CONTEXT_WINDOW: int = Field(default=15, description="Number of recent messages to include in context")

    # Admin Configuration (Document Management)
    ADMIN_USERNAME: str = Field(default="admin", description="Admin username for document management")
    ADMIN_PASSWORD: str = Field(default="admin", description="Admin password for document management")

    # Logfire Configuration (Observability)
    LOGFIRE_TOKEN: str | None = Field(
        default=None,
        description="Logfire token from https://logfire.pydantic.dev/ - leave empty to disable logging"
    )
    LOGFIRE_URL: str = Field(
        default="https://logfire.pydantic.dev",
        description="Logfire API endpoint (change if using self-hosted)"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
        "frozen": True,
    }


settings = Settings()  # type: ignore
