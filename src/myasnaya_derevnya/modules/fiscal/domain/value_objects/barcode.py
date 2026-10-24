def normalize_barcode(value: str | None) -> str | None:
    """Приводит штрихкод из чека к виду, пригодному для сопоставления.

    ОФД иногда отдаёт штрихкод строкой из нулей или с пробелами. Пустые
    значения не считаем штрихкодом, иначе они склеят разные товары.
    """

    if value is None:
        return None

    normalized = "".join(value.split())
    normalized = normalized.removeprefix("]C1").strip("'\"")
    normalized = normalized.replace("\x1d", "")
    if not normalized or set(normalized) == {"0"}:
        return None

    return normalized
