from app.schemas.common import ApiError

_DESCRIPTIONS = {
    400: "Некорректный запрос",
    401: "Требуется авторизация",
    403: "Недостаточно прав",
    404: "Не найдено",
    409: "Конфликт состояния (кулдаун, дубликат, закрытая сущность)",
    422: "Ошибка валидации",
    429: "Превышен лимит",
}


def errors(*codes: int) -> dict:
    """OpenAPI documentation of error responses (body: ApiError)."""
    return {c: {"model": ApiError, "description": _DESCRIPTIONS.get(c, "Ошибка")} for c in codes}
