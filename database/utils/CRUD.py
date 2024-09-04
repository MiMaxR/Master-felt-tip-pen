import sys
import os
import logging

current_dir = os.path.dirname(os.path.abspath(__file__))
database_dir = os.path.join(current_dir, "..", "..", "database")
sys.path.append(database_dir)

from typing import Dict, TypeVar
from peewee import ModelSelect
from common.models import db, History
import peewee as pw

T = TypeVar("T")

# Настройка логгера
logging.basicConfig(
    filename="error.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def _store_data(db_instance: pw.Database, model: pw.Model, *data: Dict[str, T]) -> None:
    """
    Сохраняет данные в базе данных.

    Параметры:
    - db_instance: pw.Database - Экземпляр базы данных.
    - model: pw.Model - Модель Peewee.
    - *data: Dict[str, T] - Данные для сохранения.

    Возвращает:
    - None
    """
    with db_instance.atomic():
        for entry in data:
            if "token_count" in entry:
                entry["token_count"] = int(entry["token_count"]) - 1
        try:
            model.insert_many(data).execute()
            logging.info("Data stored successfully.")
        except Exception as e:
            logging.error(f"Error storing data: {e}")


def _retrieve_all_data(
    db_instance: pw.Database, model: pw.Model, *columns: pw.Field
) -> ModelSelect:
    """
    Извлекает все данные из базы данных.

    Параметры:
    - db_instance: pw.Database - Экземпляр базы данных.
    - model: pw.Model - Модель Peewee.
    - *columns: pw.Field - Поля для извлечения.

    Возвращает:
    - ModelSelect: Результат запроса к базе данных.
    """
    with db_instance.atomic():
        response = model.select(*columns)

    return response


class CRUDInterface:
    """
    Интерфейс для выполнения операций CRUD.

    Методы:
    - create(): Возвращает функцию для создания записей.
    - retrieve(): Возвращает функцию для извлечения записей.
    """

    @staticmethod
    def create() -> TypeVar:
        """
        Возвращает функцию для создания записей.

        Возвращает:
        - TypeVar: Функция для сохранения данных.
        """
        return _store_data

    @staticmethod
    def retrieve() -> TypeVar:
        """
        Возвращает функцию для извлечения записей.

        Возвращает:
        - TypeVar: Функция для извлечения данных.
        """
        return _retrieve_all_data


def main():
    # Создание записи
    create_function = CRUDInterface.create()
    create_function(
        db,
        History,
        {"chat_id": 123, "name": "John", "number": "123456789", "message": "Hello"},
    )

    # Извлечение всех записей
    retrieve_function = CRUDInterface.retrieve()
    results = retrieve_function(db, History)

    # Вывод заголовков столбцов
    print(
        "{:<10} {:<20} {:<15} {:<70} {:<12} {:<20}".format(
            "Chat ID", "Name", "Number", "Message", "Token Count", "Last Generated At"
        )
    )
    print("-" * 90)  # Горизонтальная линия для разделения заголовков и данных

    # Вывод данных
    for result in results:
        print(
            "{:<10} {:<20} {:<15} {:<70} {:<12} {:<20}".format(
                result.chat_id,
                result.name,
                result.number,
                result.message,
                result.token_count,
                result.last_generated_at,
            )
        )
        logging.info(
            f"Data retrieved successfully: {result.chat_id}, {result.name}, {result.number}, {result.message}, {result.token_count}, {result.last_generated_at}"
        )


if __name__ == "__main__":
    main()
