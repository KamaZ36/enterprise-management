"""Общие настройки тестов.

Настройки приложения валидируются в момент импорта, поэтому значения по
умолчанию выставляем до того, как тесты начнут импортировать пакет.
Переменные окружения имеют приоритет над .env, так что тесты не зависят
от содержимого локального .env.

Тесты, которым нужна база, работают с отдельной БД `myasnaya_derevnya_test`,
чтобы случайно не тронуть рабочие данные. Её нужно создать и накатить
миграции:

    DB_DATABASE=myasnaya_derevnya_test alembic upgrade head
"""

import os

_DEFAULTS = {
    "DEBUG": "true",
    "DB_USER": "user",
    "DB_PASSWORD": "password",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_DATABASE": "myasnaya_derevnya_test",
    "INITIAL_ADMIN_USERNAME": "admin",
    "INITIAL_ADMIN_PASSWORD": "admin",
    "ADMIN_ROLE_CODE": "SUPER_ADMIN",
    "ADMIN_ROLE_NAME": "Технический администратор",
}

for _key, _value in _DEFAULTS.items():
    os.environ.setdefault(_key, _value)
