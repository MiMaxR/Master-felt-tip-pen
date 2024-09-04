import os

from dotenv import load_dotenv
from pydantic import SecretStr, StrictStr
from pydantic_settings import BaseSettings

load_dotenv()


class ProjectSettings(BaseSettings):
    bot_token: SecretStr = os.getenv("BOT_TOKEN", None)
    stability_ai_token: SecretStr = os.getenv("STABILITY_AI_TOKEN", None)
    stability_ai_url: StrictStr = os.getenv("STABILITY_AI_URL", None)
