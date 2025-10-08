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
    EVOLUTION_INSTANCE_NAME: str = Field(default="bot_instance")

    # API Configuration
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_DEBUG: bool = Field(default=True)

    # Webhook Configuration
    WEBHOOK_URL: str = Field(
        default="http://localhost:8000/webhook",
        description="URL where Evolution API will send webhooks",
    )
    WEBHOOK_ENABLED: bool = Field(
        default=True, description="Enable webhook configuration"
    )
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
    OPENAI_MAX_TOKENS: int = Field(default=1000)
    OPENAI_TEMPERATURE: float = Field(default=0)

    # Security
    SECRET_KEY: str

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
        "frozen": True,
    }


settings = Settings()  # type: ignore
