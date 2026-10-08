import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import auth, candidate, employer, jobs, mock_fsp, reference, testing
from app.core.config import get_settings
from app.core.errors import DomainError
from app.i18n import has, negotiate, reset_locale, set_locale, t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fsp_talent")

settings = get_settings()


def _offer_pass() -> int:
    from app.db.session import SessionLocal
    from app.services import tasks_service

    with SessionLocal() as db:
        return tasks_service.offer_all_due(db)


async def _offer_loop(minutes: int) -> None:
    """Regular tasks are offered periodically, not only when a candidate opens the page."""
    while True:
        await asyncio.sleep(minutes * 60)
        try:
            n = await run_in_threadpool(_offer_pass)
            if n:
                logger.info("regular tasks: %s new offers", n)
        except Exception:  # a failed pass must not stop the loop
            logger.exception("regular tasks: offer pass failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    loop = asyncio.create_task(_offer_loop(settings.task_offer_loop_minutes)) \
        if settings.task_offer_loop_minutes > 0 else None
    yield
    if loop:
        loop.cancel()

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
    lifespan=lifespan,
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


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    """Unknown routes and wrong methods answer in the same {code, message, details} format as every
    other error (and in the request language) instead of FastAPI's bare {"detail": "Not Found"}."""
    if exc.status_code == 404 and exc.detail in (None, "Not Found"):
        code, message = "route_not_found", t("error.route_not_found", path=request.url.path)
    elif exc.status_code == 405:
        code, message = "method_not_allowed", t("error.method_not_allowed", method=request.method)
    else:
        code, message = "http_error", str(exc.detail)
    return JSONResponse(status_code=exc.status_code, headers=getattr(exc, "headers", None),
                        content={"code": code, "message": message, "details": {"path": request.url.path}})


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


@app.get(settings.api_prefix, tags=["Служебное"], summary="Точка входа API: ссылки на документацию")
@app.get(f"{settings.api_prefix}/", include_in_schema=False)
def api_index():
    p = settings.api_prefix
    return {"name": app.title, "version": app.version, "docs": f"{p}/docs", "redoc": f"{p}/redoc",
            "openapi": f"{p}/openapi.json", "health": f"{p}/health"}


# The API lives under /api; the bare backend address (what a browser opens on :8000) leads to the docs.
@app.get("/", include_in_schema=False)
@app.get("/docs", include_in_schema=False)
def to_docs():
    return RedirectResponse(f"{settings.api_prefix}/docs")


@app.get("/redoc", include_in_schema=False)
def to_redoc():
    return RedirectResponse(f"{settings.api_prefix}/redoc")


@app.get("/openapi.json", include_in_schema=False)
def to_openapi():
    return RedirectResponse(f"{settings.api_prefix}/openapi.json")
