from fastapi import APIRouter, status

from app.api.deps import DB, Candidate, CurrentUser
from app.api.responses import errors
from app.models import CandidateProfile, Role
from app.schemas.jobs import ApplicationIn, ApplicationOut, PublicJobOut
from app.services import jobs_service, presenters

router = APIRouter(tags=["Вакансии и отклики"], responses=errors(401))


@router.get("/jobs", response_model=list[PublicJobOut],
            summary="Опубликованные вакансии (для кандидата — с % совпадения)")
def jobs(user: CurrentUser, db: DB, specialization_id: str | None = None, grade_id: str | None = None,
         q: str | None = None):
    cand = None
    if user.role == Role.CANDIDATE:
        cand = db.query(CandidateProfile).filter_by(user_id=user.id).one_or_none()
    return jobs_service.public_jobs(db, cand, specialization_id, grade_id, q)


@router.get("/jobs/{job_id}", response_model=PublicJobOut, responses=errors(404))
def job(job_id: int, user: CurrentUser, db: DB):
    return presenters.job(jobs_service.get_public(db, job_id))


@router.post("/applications", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED,
             responses=errors(403, 404, 409, 422), summary="Откликнуться на вакансию")
def apply(body: ApplicationIn, c: Candidate, db: DB):
    a = jobs_service.apply(db, c, body.job_id, body.cover_letter)
    return next(x for x in jobs_service.my_applications(db, c) if x["id"] == a.id)


@router.get("/applications", response_model=list[ApplicationOut], responses=errors(403), summary="Мои отклики")
def my_applications(c: Candidate, db: DB):
    return jobs_service.my_applications(db, c)
