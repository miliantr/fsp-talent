from fastapi import APIRouter, Query, status

from app.api.deps import DB, Employer
from app.api.responses import errors
from app.core.errors import NotFound
from app.repositories import candidates as cand_repo
from app.schemas.common import Message
from app.schemas.employer import (
    BankOut,
    CandidateDetail,
    CompanyIn,
    CompanyOut,
    CompareOut,
    EmployerDashboard,
    InvitationIn,
    InvitationOut,
    MatchListOut,
    ParseNeedIn,
    ParseNeedOut,
    RequirementIn,
    RequirementOut,
)
from app.schemas.jobs import (
    ApplicationStatusIn,
    EmployerApplicationOut,
    ReviewIn,
    SubmissionOut,
    TaskIn,
    TaskOut,
)
from app.services import employer_service, invitation_service, jobs_service, presenters, tasks_service
from app.services.matching import service as matching

router = APIRouter(prefix="/employer", tags=["Кабинет работодателя"], responses=errors(401, 403))


@router.get("/dashboard", response_model=EmployerDashboard, summary="Сводка: потребности, воронка приглашений")
def dashboard(e: Employer, db: DB):
    return employer_service.dashboard(db, e)


@router.get("/profile", response_model=CompanyOut, summary="Профиль компании")
def get_company(e: Employer):
    return employer_service.company_view(e)


@router.put("/profile", response_model=CompanyOut, responses=errors(422), summary="Обновить профиль компании")
def update_company(body: CompanyIn, e: Employer, db: DB):
    return employer_service.company_view(employer_service.update_company(db, e, body.model_dump()))


# ------------------------------------------------------------------ requirements (needs)

@router.get("/requirements", response_model=list[RequirementOut], summary="Описанные потребности")
def list_requirements(e: Employer, db: DB):
    return employer_service.jobs_view(db, e)


@router.post("/requirements", response_model=RequirementOut, status_code=status.HTTP_201_CREATED,
             responses=errors(422), summary="Описать потребность — подборка формируется сразу")
def create_requirement(body: RequirementIn, e: Employer, db: DB):
    job = employer_service.create_job(db, e, body.model_dump())
    return presenters.job(job) | {"stats": employer_service.job_stats(db, job)}


@router.post("/requirements/parse", response_model=ParseNeedOut,
             summary="Разобрать текстовое описание потребности (специализация, грейд, стек, вилка)")
def parse_requirement(body: ParseNeedIn, e: Employer):
    return employer_service.parse_need(body.text)


@router.get("/requirements/{job_id}", response_model=RequirementOut, responses=errors(404))
def get_requirement(job_id: int, e: Employer, db: DB):
    job = matching.get_job(db, e, job_id)
    return presenters.job(job) | {"stats": employer_service.job_stats(db, job)}


@router.put("/requirements/{job_id}", response_model=RequirementOut, responses=errors(404, 422),
            summary="Уточнить потребность (подборка пересчитывается)")
def update_requirement(job_id: int, body: RequirementIn, e: Employer, db: DB):
    job = employer_service.update_job(db, e, job_id, body.model_dump())
    return presenters.job(job) | {"stats": employer_service.job_stats(db, job)}


@router.delete("/requirements/{job_id}", response_model=Message, responses=errors(404), summary="Закрыть потребность")
def close_requirement(job_id: int, e: Employer, db: DB):
    employer_service.close_job(db, e, job_id)
    return Message(message="Потребность закрыта")


@router.get("/requirements/{job_id}/matches", response_model=MatchListOut, responses=errors(404),
            summary="Ранжированная подборка с объяснением и группировкой по категориям")
def matches(job_id: int, e: Employer, db: DB,
            grades: list[str] = Query(default=[]), categories: list[str] = Query(default=[]),
            skills: list[str] = Query(default=[]), has_fsp: bool | None = None,
            min_score: int | None = Query(default=None, ge=0, le=100), shortlisted: bool | None = None,
            refresh: bool = False, limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    """Фильтры уточняют уже полученную подборку: снимок ранжирования хранится в БД
    (match_results), поэтому подборка и отметки shortlist не теряются."""
    job = matching.get_job(db, e, job_id)
    return matching.list_matches(db, e, job, grades=grades or None, categories=categories or None,
                                 skills=skills or None, has_fsp=has_fsp, min_score=min_score,
                                 shortlisted=shortlisted, refresh=refresh, limit=limit, offset=offset)


@router.post("/requirements/{job_id}/shortlist/{candidate_id}", response_model=Message, responses=errors(404))
def shortlist(job_id: int, candidate_id: int, e: Employer, db: DB, value: bool = True):
    matching.set_shortlist(db, matching.get_job(db, e, job_id), candidate_id, value)
    return Message(message="ok")


@router.get("/requirements/{job_id}/compare", response_model=CompareOut, responses=errors(404),
            summary="Почему кандидат A выше кандидата B")
def compare(job_id: int, a: int, b: int, e: Employer, db: DB):
    job = matching.get_job(db, e, job_id)
    ca, cb = cand_repo.get_with_relations(db, a), cand_repo.get_with_relations(db, b)
    if not ca or not cb or not ca.is_searchable or not cb.is_searchable:
        raise NotFound("Кандидат не найден")
    return matching.compare(db, job, ca, cb)


# ------------------------------------------------------------------ candidates bank

@router.get("/candidates", response_model=BankOut, summary="Банк кандидатов с фильтрами")
def candidates(e: Employer, db: DB, specialization_id: str | None = None,
               grades: list[str] = Query(default=[]), categories: list[str] = Query(default=[]),
               skills: list[str] = Query(default=[]), has_fsp: bool | None = None,
               limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    return matching.search_bank(db, e, specialization=specialization_id, grades=grades or None,
                                categories=categories or None, skills=skills or None, has_fsp=has_fsp,
                                limit=limit, offset=offset)


@router.get("/candidates/{candidate_id}", response_model=CandidateDetail, responses=errors(404),
            summary="Профиль кандидата (контакты — только после принятия приглашения или отклика)")
def candidate(candidate_id: int, e: Employer, db: DB, requirement_id: int | None = None):
    job = matching.get_job(db, e, requirement_id) if requirement_id else None
    return matching.candidate_detail(db, e, candidate_id, job)


# ------------------------------------------------------------------ invitations

@router.get("/invitations", response_model=list[InvitationOut], summary="История приглашений и статусы")
def invitations(e: Employer, db: DB, status: str | None = None):
    return [presenters.invitation(i, True, invitation_service.contacts_for(db, e, i.candidate))
            for i in invitation_service.for_employer(db, e, status)]


@router.post("/invitations", response_model=InvitationOut, status_code=status.HTTP_201_CREATED,
             responses=errors(404, 409, 422, 429), summary="Пригласить кандидата (зарплата обязательна)")
def invite(body: InvitationIn, e: Employer, db: DB):
    inv = invitation_service.create(db, e, **body.model_dump())
    return presenters.invitation(inv, True, invitation_service.contacts_for(db, e, inv.candidate))


@router.post("/invitations/{inv_id}/withdraw", response_model=InvitationOut, responses=errors(404, 409))
def withdraw(inv_id: int, e: Employer, db: DB):
    inv = invitation_service.withdraw(db, e, inv_id)
    return presenters.invitation(inv, True, invitation_service.contacts_for(db, e, inv.candidate))


# ------------------------------------------------------------------ applications (job board)

@router.get("/applications", response_model=list[EmployerApplicationOut], summary="Отклики на вакансии")
def applications(e: Employer, db: DB, job_id: int | None = None):
    return jobs_service.employer_applications(db, e, job_id)


@router.post("/applications/{app_id}/status", response_model=Message, responses=errors(404, 422))
def application_status(app_id: int, body: ApplicationStatusIn, e: Employer, db: DB):
    jobs_service.set_application_status(db, e, app_id, body.status)
    return Message(message="Статус обновлён")


# ------------------------------------------------------------------ regular short tasks

@router.get("/tasks", response_model=list[TaskOut], summary="Короткие задания компании")
def tasks(e: Employer, db: DB):
    return tasks_service.for_employer(db, e)


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED, responses=errors(422))
def create_task(body: TaskIn, e: Employer, db: DB):
    t = tasks_service.create(db, e, body.specialization_id, body.title, body.description)
    return next(x for x in tasks_service.for_employer(db, e) if x["id"] == t.id)


@router.get("/tasks/{task_id}/submissions", response_model=list[SubmissionOut], responses=errors(404))
def task_submissions(task_id: int, e: Employer, db: DB):
    return tasks_service.submissions(db, e, task_id)


@router.post("/submissions/{submission_id}/review", response_model=Message, responses=errors(404, 422))
def review(submission_id: int, body: ReviewIn, e: Employer, db: DB):
    tasks_service.review(db, e, submission_id, body.rating, body.comment)
    return Message(message="Оценка сохранена")
