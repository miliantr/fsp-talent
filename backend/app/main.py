import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, candidate, employer, jobs, mock_fsp, reference, testing
from app.core.config import get_settings
from app.core.errors import DomainError

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


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    errs = [{"loc": [str(x) for x in e["loc"]], "msg": e["msg"]} for e in exc.errors()]
    first = errs[0]["msg"] if errs else "Некорректные данные"
    return JSONResponse(status_code=422, content={"code": "validation_failed", "message": first,
                                                  "details": {"errors": errs}})


for r in (auth.router, reference.router, candidate.router, testing.router, employer.router, jobs.router,
          mock_fsp.router):
    app.include_router(r, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health", tags=["Служебное"])
def health():
    return {"status": "ok"}
