import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, candidate, employer, jobs, mock_fsp, reference, testing
from app.core.config import get_settings
from app.core.errors import DomainError
from app.i18n import has, negotiate, reset_locale, set_locale, t

logging.basicConfig(level=logging.INFO)

settings = get_settings()

DESCRIPTION = """
**FSP Talent** — платформа подбора ИТ-специалистов с обратной механикой: кандидаты автоматически
категоризируются по объективно подтверждённому профилю (опрос → тест на заявленный грейд →
категория «специализация · грейд» + достижения ФСП), а работодатель описывает потребность,
получает ранжированную и объяснимую подборку и сам приглашает кандидата с зарплатной вилкой.

Авторизация: `Authorization: Bearer <JWT>` (получить через `/auth/login` или `/auth/verify-email`).
Ошибки возвращаются в формате `ApiError {code, message, details}`.
"""

app = FastAPI(
    title="FSP Talent API",
    version="1.0.0",
    description=DESCRIPTION,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
)

class LocaleMiddleware:
    """Request locale from Accept-Language (the web client sends its UI language with every call).
    Pure ASGI so the context variable is visible to the endpoint and to exception handlers."""

    def __init__(self, asgi_app):
        self.app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        header = next((v.decode("latin-1") for k, v in scope["headers"] if k == b"accept-language"), None)
        lang = negotiate(header)
        token = set_locale(lang)

        async def send_with_language(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += [(b"content-language", lang.encode()), (b"vary", b"Accept-Language")]
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_language)
        finally:
            reset_locale(token)


app.add_middleware(LocaleMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code,
                        content={"code": exc.code, "message": exc.message, "details": exc.details})


_LIMITS = {"greater_than": "gt", "greater_than_equal": "ge", "less_than": "lt", "less_than_equal": "le"}


def validation_message(err: dict) -> str:
    """Pydantic error -> a localized, human-readable message naming the field."""
    name = str(err["loc"][-1]) if err.get("loc") else ""
    field = t(f"field.{name}") if has(f"field.{name}") else name
    kind, ctx = err.get("type", ""), err.get("ctx") or {}
    if kind == "missing":
        return t("validation.missing", field=field)
    if kind == "string_too_short":
        return t("validation.too_short", field=field, min=ctx.get("min_length", 0))
    if kind == "string_too_long":
        return t("validation.too_long", field=field, max=ctx.get("max_length", 0))
    if kind in _LIMITS:
        return t(f"validation.{kind}", field=field, limit=ctx.get(_LIMITS[kind], 0))
    if kind == "salary_range":
        return t("error.salary_range_inverted")
    if name == "email" or "email" in str(err.get("msg", "")).lower():
        return t("validation.email")
    return t("validation.invalid", field=field)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    errs = [{"loc": [str(x) for x in e["loc"]], "msg": validation_message(e), "type": e.get("type")}
            for e in exc.errors()]
    first = errs[0]["msg"] if errs else t("error.invalid_data")
    return JSONResponse(status_code=422, content={"code": "validation_failed", "message": first,
                                                  "details": {"errors": errs}})


for r in (auth.router, reference.router, candidate.router, testing.router, employer.router, jobs.router,
          mock_fsp.router):
    app.include_router(r, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health", tags=["Служебное"])
def health():
    return {"status": "ok"}
