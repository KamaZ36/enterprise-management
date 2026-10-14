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
    "LOGIN_CODE_SECRET": "pytest-login-code-secret",
}

for _key, _value in _DEFAULTS.items():
    os.environ.setdefault(_key, _value)
