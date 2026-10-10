def escape_like(value: str) -> str:
    """Экранирует служебные символы LIKE: без этого «50%» стало бы шаблоном."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def like_pattern(value: str) -> str:
    """Шаблон для ILIKE: поиск подстроки с экранированием служебных символов."""
    return f"%{escape_like(value)}%"
