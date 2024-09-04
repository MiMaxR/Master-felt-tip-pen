from settings import ProjectSettings
from stability_API.stability_ai import ImageGenerationService
from my_bot.my_bot import Bot
from database.common.models import db, History
from database.core import CRUDInterface

import logging


def main() -> None:
    """
    Основная функция запуска бота.
    """

    # Конфигурация логгера
    logging.basicConfig(
        filename="error.log",
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    try:
        settings: ProjectSettings = ProjectSettings()
        TOKEN: str = settings.bot_token.get_secret_value()
        STABILITY_AI_TOKEN: str = settings.stability_ai_token.get_secret_value()
        STABILITY_AI_URL: str = settings.stability_ai_url

        db.connect()
        db.create_tables([History])

        crud: CRUDInterface = CRUDInterface()

        bot: Bot = Bot(
            TOKEN, ImageGenerationService(STABILITY_AI_TOKEN, STABILITY_AI_URL), crud
        )

        bot.start()
    except RuntimeError as e:
        logging.error(f"Ошибка: {e}")
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
