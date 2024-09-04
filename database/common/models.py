from datetime import datetime
import peewee as pw

db = pw.SqliteDatabase("lecture.db")


class ModelBase(pw.Model):
    """
    Базовая модель, содержащая поле для хранения времени создания записи.
    """

    # created_at = pw.DateTimeField(default=datetime.now)

    class Meta:
        database = db


class History(ModelBase):
    """
    Модель истории пользовательских действий.

    Поля:
    - chat_id: int - Идентификатор чата пользователя.
    - name: str - Имя пользователя.
    - number: str - Номер телефона пользователя.
    - message: str - Текст сообщения пользователя.
    - token_count: int - Количество доступных токенов для пользователя (по умолчанию 10).
    - last_generated_at: datetime - Время последней генерации токенов.

    Методы:
    - update_token_count(cls, chat_id): Обновляет количество доступных токенов для пользователя.
    """

    chat_id = pw.IntegerField()
    name = pw.TextField()
    number = pw.TextField()
    message = pw.TextField()
    token_count = pw.IntegerField(default=10)
    last_generated_at = pw.DateTimeField(default=datetime.now)

    @classmethod
    def update_token_count(cls, chat_id):
        """
        Обновляет количество доступных токенов для пользователя.

        Параметры:
        - chat_id: int - Идентификатор чата пользователя.

        Возвращает:
        - bool: True, если обновление прошло успешно, False в противном случае.
        """
        try:
            user_history = cls.get(cls.chat_id == chat_id)

            current_date = datetime.now().date()
            if user_history.last_generated_at.date() < current_date:
                user_history.token_count = 50

            if user_history.token_count > 0:
                user_history.token_count -= 1
                user_history.last_generated_at = datetime.now()
                user_history.save()
                return True
            else:
                return False
        except cls.DoesNotExist:
            return False
