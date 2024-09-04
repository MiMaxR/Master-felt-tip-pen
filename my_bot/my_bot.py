import os
import sys
import logging

# Добавляем пути к модулям в пути поиска Python
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

# Импортируем модули
import base64
import io
from mtranslate import translate
from typing import List, Dict, Any
from telebot import TeleBot, types
from stability_API.stability_ai import ImageGenerationService
from peewee import fn

from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

from settings import ProjectSettings
from database.core import CRUDInterface
from database.common.models import db, History


def encrypt(text: str | int, key: int) -> str:
    """
    Функция шифрования текста методом Цезаря с использованием ключа.

    Параметры:
    - text (str | int): Текст, который требуется зашифровать. Может быть строкой или числом.
    - key (int): Ключ для шифрования.

    Возвращает:
    - str: Зашифрованный текст.

    """
    text = str(text)
    encrypted_text = ""
    key_length = len(str(key))

    for i, char in enumerate(text):
        shift = int(str(key)[i % key_length])
        if "a" <= char <= "z":
            encrypted_text += chr((ord(char) - ord("a") + shift) % 26 + ord("a"))
        elif "A" <= char <= "Z":
            encrypted_text += chr((ord(char) - ord("A") + shift) % 26 + ord("A"))
        elif "а" <= char <= "я":
            encrypted_text += chr((ord(char) - ord("а") + shift) % 32 + ord("а"))
        elif "А" <= char <= "Я":
            encrypted_text += chr((ord(char) - ord("А") + shift) % 32 + ord("А"))
        else:
            encrypted_text += char

    return encrypted_text


def decrypt(encrypted_text: str | int, key: int) -> str:
    """
    Функция дешифрования текста, зашифрованного методом Цезаря.

    Параметры:
    - encrypted_text (str | int): Зашифрованный текст. Может быть строкой или числом.
    - key (int): Ключ для дешифрования.

    Возвращает:
    - str: Расшифрованный текст.

    """
    encrypted_text = str(encrypted_text)
    decrypted_text = ""
    key_length = len(str(key))

    for i, char in enumerate(encrypted_text):
        shift = int(str(key)[i % key_length])
        if "a" <= char <= "z":
            decrypted_text += chr((ord(char) - ord("a") - shift) % 26 + ord("a"))
        elif "A" <= char <= "Z":
            decrypted_text += chr((ord(char) - ord("A") - shift) % 26 + ord("A"))
        elif "а" <= char <= "я":
            decrypted_text += chr((ord(char) - ord("а") - shift) % 32 + ord("а"))
        elif "А" <= char <= "Я":
            decrypted_text += chr((ord(char) - ord("А") - shift) % 32 + ord("А"))
        else:
            decrypted_text += char

    return decrypted_text


class Bot:
    """
    Класс Telegram-бота, который генерирует изображения на основе текстовых описаний.

    Атрибуты:
        token (str): Токен Telegram Bot API.
        image_generation_service (ImageGenerationService): Экземпляр сервиса генерации изображений.
        crud (object): Объект, предоставляющий операции CRUD для базы данных.
        bot (TeleBot): Экземпляр библиотеки TeleBot для обработки функциональности Telegram-бота.
        is_generating (bool): Флаг, указывающий, идет ли процесс генерации изображения.
    """

    def __init__(
        self, token: str, image_generation_service: ImageGenerationService, crud
    ) -> None:
        print("Bot is starting...")
        """
        Инициализирует экземпляр класса Bot.

        Аргументы:
            token (str): Токен Telegram Bot API.
            image_generation_service (ImageGenerationService): Экземпляр сервиса генерации изображений.
            crud (object): Объект, предоставляющий операции CRUD для базы данных.
        """

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler = logging.FileHandler("error.log")
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        self.token: str = token
        self.bot: TeleBot = TeleBot(token)
        self.image_generation_service: ImageGenerationService = image_generation_service
        self.is_generating: bool = False
        self.crud = crud

    def send_main_menu(self, message: types.Message) -> None:
        """
        Отправляет основное меню с вариантами действий пользователю.

        Аргументы:
            message (types.Message): Объект сообщения, полученный от Telegram.
        """

        try:
            markup: types.ReplyKeyboardMarkup = types.ReplyKeyboardMarkup(
                resize_keyboard=True
            )
            button_generator: types.KeyboardButton = types.KeyboardButton(
                "Генерировать изображение 🌄"
            )
            button_info: types.KeyboardButton = types.KeyboardButton("Инструкция ❓")
            markup.add(button_generator)
            markup.add(button_info)
            self.bot.send_message(
                message.chat.id, "Выберите действие:", reply_markup=markup
            )
        except Exception as e:
            self.logger.error(f"В send_main_menu методе произошла ошибка: {str(e)}")

    def generate_and_send_image(
        self, message: types.Message, text_description: str
    ) -> None:
        """
        Генерирует изображение на основе предоставленного текстового описания и отправляет его пользователю.

        Аргументы:
            message (types.Message): Объект сообщения, полученный от Telegram.
            text_description (str): Текстовое описание изображения для генерации.
        """
        try:
            chat_id: int = message.chat.id
            encrypt_id = encrypt(chat_id, chat_id)
            if History.update_token_count(encrypt_id):
                user_name: str = (
                    message.from_user.first_name or message.from_user.username
                )
                generating_message: types.Message = self.bot.send_message(
                    message.chat.id, "Идёт🚶‍♂️ генерация изображения... 😊"
                )
                try:
                    images: List[Dict[str, Any]] = (
                        self.image_generation_service.generate_image(text_description)
                    )
                    for image in images:
                        img_data: bytes = base64.b64decode(image["base64"])
                        img_io: io.BytesIO = io.BytesIO(img_data)
                        self.bot.send_photo(message.chat.id, img_io)
                    self.bot.delete_message(
                        message.chat.id, generating_message.message_id
                    )
                    self.send_main_menu(message)
                    token_count: int = History.get(
                        History.chat_id == encrypt_id
                    ).token_count

                    self.crud.create()(
                        db,
                        History,
                        {
                            "chat_id": encrypt_id,
                            "name": user_name,
                            "number": message.message_id,
                            "message": encrypt(message.text, chat_id),
                            "token_count": token_count,
                        },
                    )
                except Exception as e:
                    self.bot.reply_to(message, f"Произошла ошибка: {str(e)}")
            else:
                self.bot.reply_to(
                    message,
                    "А всё, у Вас недостаточно токенов для генерации изображения. Подождите денёк. Токены восстонавливаются раз в день",
                )
        except Exception as e:
            self.logger.error(
                f"В generate_and_send_image методе произошла ошибка: {str(e)}"
            )

    def start(self) -> None:
        """
        Метод запускает бота и обрабатывает различные типы сообщений пользователя.

        Бот реагирует на команды, сообщения и нажатия кнопок, выполняя соответствующие действия.
        """

        try:

            @self.bot.message_handler(commands=["start", "menu"])
            def send_welcome(message: types.Message) -> None:
                """
                Приветствует пользователя и отправляет основное меню.

                Аргументы:
                    message (types.Message): Объект сообщения, полученный от Telegram.
                """
                user_id: int = message.chat.id
                user_name: str = (
                    message.from_user.first_name or message.from_user.username
                )

                self.crud.create()(
                    db,
                    History,
                    {
                        "chat_id": encrypt(message.chat.id, message.chat.id),
                        "name": user_name,
                        "number": message.message_id,
                        "message": encrypt(message.text, message.chat.id),
                    },
                )
                welcome_message: str = f"""Здравствуй, {user_name}🙃! Я твой бот 'Мастер фломастер 😉'. 

    Хочешь создать красивое изображение по своему описанию? Просто напиши мне, что ты хочешь увидеть, и я нарисую это для тебя!

    Список команд:
    /menu - моё главное меню
    /low - наименьшее количество запросов
    /high - наибольшее количество запросов
    /history - история Ваших запросов
    /tokens - токены
    /info - информация
    """
                self.bot.reply_to(message, welcome_message)
                self.send_main_menu(message)

            @self.bot.message_handler(commands=["history"])
            def send_history(message: types.Message) -> None:
                """
                Отправляет пользовательскую историю запросов, исключая запросы, начинающиеся с '/'.

                Аргументы:
                    message (types.Message): Объект сообщения, полученный от Telegram.
                """
                user_name: str = (
                    message.from_user.first_name or message.from_user.username
                )
                user_id: int = message.chat.id
                encrypt_id: str = encrypt(message.chat.id, message.chat.id)
                history_entries = (
                    History.select()
                    .where(
                        (History.chat_id == encrypt_id)
                        & ~(History.message.startswith("/"))
                    )
                    .order_by(History.last_generated_at.desc())
                    .limit(10)
                )

                history_text: str = f"Последние 10 запросов пользователя {user_name}:\n"
                for entry in history_entries:
                    history_text += f"Сообщение: {decrypt(entry.message, user_id)}\n"

                self.crud.create()(
                    db,
                    History,
                    {
                        "chat_id": encrypt(message.chat.id, message.chat.id),
                        "name": user_name,
                        "number": message.message_id,
                        "message": encrypt(message.text, message.chat.id),
                    },
                )
                self.bot.send_message(message.chat.id, history_text)

            @self.bot.message_handler(commands=["low"])
            def send_low_months(message: types.Message) -> None:
                """
                Отправляет месяц с наименьшим количеством запросов.

                Аргументы:
                    message (types.Message): Объект сообщения, полученный от Telegram.
                """
                user_id: int = message.chat.id
                user_name: str = (
                    message.from_user.first_name or message.from_user.username
                )

                self.crud.create()(
                    db,
                    History,
                    {
                        "chat_id": encrypt(message.chat.id, message.chat.id),
                        "name": user_name,
                        "number": message.message_id,
                        "message": encrypt(message.text, message.chat.id),
                    },
                )
                months = (
                    History.select(
                        fn.strftime("%Y-%m", History.last_generated_at).alias("month"),
                        fn.COUNT(History.id).alias("total_requests"),
                    )
                    .where(
                        (History.chat_id == user_id)
                        & ~(History.message.startswith("/"))
                    )
                    .group_by("month")
                    .order_by("total_requests")
                )

                if months:
                    lowest_month = min(months, key=lambda x: x.total_requests)
                    self.bot.send_message(
                        message.chat.id,
                        f"Наименьшее количество запросов у вас было в месяце {lowest_month.month}, всего {lowest_month.total_requests} запросов.",
                    )
                else:
                    self.bot.send_message(
                        message.chat.id,
                        "У вас нет запросов, которые не начинаются с символа '/'.",
                    )

            @self.bot.message_handler(commands=["high"])
            def send_high_months(message: types.Message) -> None:
                """
                Отправляет месяц с наибольшим количеством запросов.

                Аргументы:
                    message (types.Message): Объект сообщения, полученный от Telegram.
                """
                user_id: int = message.chat.id
                user_name: str = (
                    message.from_user.first_name or message.from_user.username
                )

                self.crud.create()(
                    db,
                    History,
                    {
                        "chat_id": encrypt(message.chat.id, message.chat.id),
                        "name": user_name,
                        "number": message.message_id,
                        "message": encrypt(message.text, message.chat.id),
                    },
                )
                months = (
                    History.select(
                        fn.strftime("%Y-%m", History.last_generated_at).alias("month"),
                        fn.COUNT(History.id).alias("total_requests"),
                    )
                    .where(
                        (History.chat_id == user_id)
                        & ~(History.message.startswith("/"))
                    )
                    .group_by("month")
                    .order_by("total_requests")
                )

                if months:
                    highest_month = max(months, key=lambda x: x.total_requests)
                    self.bot.send_message(
                        message.chat.id,
                        f"Наибольшее количество запросов у вас было в месяце {highest_month.month}, всего {highest_month.total_requests} запросов.",
                    )
                else:
                    self.bot.send_message(
                        message.chat.id,
                        "У вас нет запросов, которые не начинаются с символа '/'.",
                    )

            @self.bot.message_handler(
                func=lambda message: message.text == "Генерировать изображение 🌄"
            )
            def handle_generate_button(message: types.Message) -> None:
                """
                Обрабатывает нажатие кнопки "Генерировать изображение".

                Аргументы:
                    message (types.Message): Объект сообщения, полученный от Telegram.
                """
                self.is_generating = False
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                button_start_generate = types.KeyboardButton("Начать генерацию 🎨")
                button_settings_generate = types.KeyboardButton("Токены 💰")
                button_back = types.KeyboardButton("Вернуться в меню ⬅️")
                markup.add(button_start_generate, button_settings_generate)
                markup.row(button_back)
                self.bot.send_message(
                    message.chat.id,
                    "Нажмите 'Начать генерацию' для создания изображения.",
                    reply_markup=markup,
                )

            @self.bot.message_handler(
                func=lambda message: message.text == "Инструкция ❓"
                or message.text == "/info"
            )
            def handle_generate_button(message: types.Message) -> None:
                """
                Обрабатывает нажатие кнопки "Инструкция".

                Аргументы:
                    message (types.Message): Объект сообщения, полученный от Telegram.
                """

                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                button_back = types.KeyboardButton("Вернуться в меню ⬅️")
                markup.add(button_back)
                instruction_text: str = """
                Привет! Я - Мастер фломастер, ваш личный художник-бот! 🎨

            Хочешь создать красивое изображение по своему описанию? Просто напиши мне, что ты хочешь увидеть, и я нарисую это для тебя!

            Вот моя инструкция 🙃:
                
                1. Нажмите кнопку "Генерировать изображение 🌄".
                2. Далее нажмите "Начать генерацию 🎨".
                3. Введите краткое описание для изображения и отправьте мне
                4. Дождитесь генерации изображения. После этого вы можете продолжить генерацию новых изображений или вернуться в главное меню.

            Обратите внимание❗️ Количество генераций ограничено. На день даётся 50 токенов. Один токен - одна картинка.
            Посмотреть токены можно нажав на кнопку Токены 💰 или написав /tokens.
            Для получения более подробной инструкции по использованию других функций, просто напишите /menu.

            Всего хорошего! Буду рад Вам помочь 🫠
                """
                self.bot.send_message(
                    message.chat.id, instruction_text, reply_markup=markup
                )

            @self.bot.message_handler(
                func=lambda message: message.text == "Начать генерацию 🎨"
                and not self.is_generating
            )
            def handle_generate_start(message: types.Message) -> None:
                """
                Обрабатывает начало процесса генерации изображения.

                Аргументы:
                    message (types.Message): Объект сообщения, полученный от Telegram.
                """
                self.is_generating = True
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                button_return_menu = types.KeyboardButton("Вернуться в меню ⬅️")
                markup.add(button_return_menu)
                self.bot.send_message(
                    message.chat.id,
                    "Напишите мне краткое описание изображения",
                    reply_markup=markup,
                )

            @self.bot.message_handler(
                func=lambda message: message.text == "Токены 💰"
                or message.text == "/tokens"
            )
            def handle_generate_settings(message: types.Message) -> None:
                """
                Обрабатывает запросы информации о токенах.

                Аргументы:
                    message (types.Message): Объект сообщения, полученный от Telegram.
                """
                chat_id: str = encrypt(message.chat.id, message.chat.id)
                try:
                    user_history = History.get(History.chat_id == chat_id)
                    remaining_tokens: int = user_history.token_count
                    self.bot.send_message(
                        message.chat.id,
                        f"На сегодня осталось: {remaining_tokens} токен",
                    )
                except History.DoesNotExist:
                    self.bot.reply_to(message, "Ошибка: у вас нет истории запросов.")

            @self.bot.message_handler(
                func=lambda message: message.text == "Вернуться в меню ⬅️"
            )
            def handle_return_to_menu(message: types.Message) -> None:
                """
                Обрабатывает возвращение в основное меню.

                Аргументы:
                    message (types.Message): Объект сообщения, полученный от Telegram.
                """
                self.send_main_menu(message)

            @self.bot.message_handler(content_types=["text"])
            def handle_generate_description(message: types.Message) -> None:
                """
                Обрабатывает текстовое описание для генерации изображения.

                Аргументы:
                    message (types.Message): Объект сообщения, полученный от Telegram.
                """
                if self.is_generating:
                    try:
                        if message.text == "Вернуться в меню ⬅️":
                            self.send_main_menu(message)
                            self.is_generating = False
                        else:
                            text_description: str = message.text
                            if message.from_user.language_code == "ru":
                                text_description = translate(text_description, "en")
                            self.generate_and_send_image(message, text_description)
                            self.is_generating = False
                    except Exception as e:
                        self.bot.reply_to(message, f"Произошла ошибка: {str(e)}")

            @self.bot.message_handler(func=lambda message: True)
            def handle_other_messages(message: types.Message) -> None:
                """
                Обрабатывает другие сообщения пользователя.

                Аргументы:
                    message (types.Message): Объект сообщения, полученный от Telegram.
                """
                if not self.is_generating:
                    self.bot.reply_to(
                        message, "Извините, я не могу обработать ваш запрос."
                    )

            self.bot.polling()
        except Exception as e:
            self.logger.error(f"Произошла ошибка в методе start: {str(e)}")


def main() -> None:
    """
    Основная функция запуска бота.
    """
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


if __name__ == "__main__":
    main()
