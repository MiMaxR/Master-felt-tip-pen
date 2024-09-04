import os
import logging
from typing import List, Dict, Any
import requests
from PIL import Image
import base64
import io
import uuid

from dotenv import load_dotenv

load_dotenv()

# Конфигурация логгера
logging.basicConfig(
    filename="error.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class ImageGenerationService:
    """
    Сервис для генерации изображений на основе текстовых описаний.

    Атрибуты:
        _token (str): Токен для аутентификации в API сервиса генерации изображений.
        _url (str): URL эндпоинта API сервиса генерации изображений.
    """

    def __init__(self, token: str, url: str) -> None:
        """
        Инициализирует экземпляр класса ImageGenerationService.

        Аргументы:
            token (str): Токен для аутентификации в API сервиса генерации изображений.
            url (str): URL эндпоинта API сервиса генерации изображений.
        """
        self._token = token
        self._url = url

    def generate_image(self, text_description: str) -> List[Dict[str, Any]]:
        """
        Генерирует изображение на основе предоставленного текстового описания.

        Аргументы:
            text_description (str): Текстовое описание для генерации изображения.

        Возвращает:
            List[Dict[str, Any]]: Список словарей, каждый из которых содержит информацию об изображении.

        Исключения:
            RuntimeError: Если произошла ошибка при генерации изображения.

        """
        body = {
            "steps": 40,
            "width": 1024,
            "height": 1024,
            "seed": 0,
            "cfg_scale": 5,
            "samples": 1,
            "text_prompts": [{"text": text_description, "weight": 1}],
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }
        response = requests.post(self._url, headers=headers, json=body)
        if response.status_code == 200:
            data = response.json()
            return data.get("artifacts", [])
        else:
            error_message = (
                f"Ошибка при генерации изображения. Код ошибки: {response.status_code}"
            )
            logging.error(error_message)
            raise RuntimeError("Ошибка при генерации изображения 😢")


def main() -> None:
    """
    Главная функция программы.
    """
    stability_ai_token: str = os.getenv("STABILITY_AI_TOKEN")
    stability_ai_url: str = os.getenv("STABILITY_AI_URL")

    if not stability_ai_token or not stability_ai_url:
        error_message = "Не удалось получить токен и URL сервиса из переменных среды."
        logging.error(error_message)
        print(error_message)
        return

    testImageGenerationService: ImageGenerationService = ImageGenerationService(
        stability_ai_token, stability_ai_url
    )
    text_description: str = input("Введите запрос на генерацию изображения: ")
    try:
        generated_images: List[Dict[str, Any]] = (
            testImageGenerationService.generate_image(text_description)
        )
        if generated_images:
            # Создание папки для сохранения изображения, если её нет
            result_dir: str = "result_generate"
            if not os.path.exists(result_dir):
                os.makedirs(result_dir)

            for image_data in generated_images:
                img_data: bytes = base64.b64decode(image_data["base64"])
                img_io: io.BytesIO = io.BytesIO(img_data)
                image: Image.Image = Image.open(img_io)

                # Генерация уникального имени для изображения
                unique_filename: str = str(uuid.uuid4()) + ".jpg"
                image_filename: str = os.path.join(result_dir, unique_filename)
                image_path: str = os.path.join(os.getcwd(), image_filename)
                image.save(image_path)

                print(
                    f"Изображение успешно сгенерировано и сохранено как {image_path}."
                )
        else:
            error_message = "Нет данных об изображении после генерации."
            logging.error(error_message)
            print(error_message)
    except RuntimeError as e:
        logging.error(f"Ошибка при генерации изображения: {e}")
        print(f"Ошибка при генерации изображения: {e}")


if __name__ == "__main__":
    main()
