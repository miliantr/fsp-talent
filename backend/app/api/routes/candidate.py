from fastapi import APIRouter, File, UploadFile

from app.api.deps import DB, Candidate
from app.api.responses import errors
from app.i18n import t
from app.schemas.candidate import (
    CandidateProfileIn,
    CandidateProfileOut,
    CandidateSettings,
    CandidateSettingsIn,
    FSPConfirmIn,
    FSPLinkIn,
    FSPLinkOut,
    FSPOut,
    ResumeParseOut,
)
from app.schemas.common import Message, SpecId
from app.schemas.employer import InvitationOut, ReportIn, RespondIn
from app.schemas.jobs import CandidateDashboard, SubmissionIn, TaskOut
from app.services import (
    candidate_service,
    categories,
    fsp_service,
    invitation_service,
    presenters,
    tasks_service,
)

router = APIRouter(prefix="/candidate", tags=["Кабинет кандидата"], responses=errors(401, 403))


@router.get("/dashboard", response_model=CandidateDashboard, summary="Сводка: категория, грейд, шаги, приглашения")
def dashboard(c: Candidate, db: DB):
    return candidate_service.dashboard(db, c)


@router.get("/profile", response_model=CandidateProfileOut, summary="Профиль и резюме")
def get_profile(c: Candidate, db: DB):
    return candidate_service.profile_view(db, c)


@router.put("/profile", response_model=CandidateProfileOut, responses=errors(422),
            summary="Обновить профиль, опрос (специализация, грейд) и навыки")
def update_profile(body: CandidateProfileIn, c: Candidate, db: DB):
    data = body.model_dump(exclude_unset=True)
    if body.skills is not None:
        data["skills"] = [s.model_dump() for s in body.skills]
    return candidate_service.profile_view(db, candidate_service.update_profile(db, c, data))


@router.put("/categories/{specialization_id}/primary", response_model=CandidateProfileOut, responses=errors(404),
            summary="Сделать подтверждённую категорию основной")
def set_primary_category(specialization_id: SpecId, c: Candidate, db: DB):
    categories.set_primary(db, c, specialization_id)
    return candidate_service.profile_view(db, c)


@router.post("/resume/parse", response_model=ResumeParseOut, responses=errors(422),
             summary="Распознать PDF-резюме (данные не сохраняются до подтверждения)")
async def parse_resume(c: Candidate, file: UploadFile = File(...)):
    data = await file.read()
    return candidate_service.parse_resume(c, file.filename or "resume.pdf", data)


@router.get("/settings", response_model=CandidateSettings, summary="Настройки приватности и согласия")
def get_settings(c: Candidate):
    return candidate_service.settings_view(c)


@router.put("/settings", response_model=CandidateSettings, summary="Изменить приватность и согласия")
def update_settings(body: CandidateSettingsIn, c: Candidate, db: DB):
    return candidate_service.settings_view(candidate_service.update_settings(db, c, body.model_dump()))


# ------------------------------------------------------------------ FSP

def _fsp_out(c) -> dict:
    return {"linked": bool(c.fsp_id), "fsp_id": c.fsp_id, "pending_fsp_id": c.fsp_pending_id,
            "summary": presenters.fsp_summary(fsp_service.summary_for(c, None)),
            "profile": presenters.fsp_profile(c.fsp_profile)}


@router.get("/fsp", response_model=FSPOut, summary="Достижения ФСП (пустой список — это нормально)")
def get_fsp(c: Candidate):
    return _fsp_out(c)


@router.post("/fsp/link", response_model=FSPLinkOut, responses=errors(404, 409),
             summary="Привязать ФСП ID (при несовпадении e-mail — подтверждение кодом)")
def link_fsp(body: FSPLinkIn, c: Candidate, db: DB):
    return fsp_service.request_link(db, c, body.fsp_id)


@router.post("/fsp/confirm", response_model=FSPOut, responses=errors(404, 409, 422),
             summary="Подтвердить привязку ФСП ID кодом")
def confirm_fsp(body: FSPConfirmIn, c: Candidate, db: DB):
    fsp_service.confirm_link(db, c, body.code)
    return _fsp_out(c)


@router.post("/fsp/sync", response_model=FSPOut, responses=errors(404, 422), summary="Обновить данные из реестра")
def sync_fsp(c: Candidate, db: DB):
    fsp_service.sync(db, c)
    return _fsp_out(c)


@router.delete("/fsp/link", response_model=FSPOut, summary="Отвязать ФСП ID")
def unlink_fsp(c: Candidate, db: DB):
    fsp_service.unlink(db, c)
    return _fsp_out(c)


# ------------------------------------------------------------------ invitations

@router.get("/invitations", response_model=list[InvitationOut], summary="Входящие приглашения")
def invitations(c: Candidate, db: DB):
    return [presenters.invitation(i, False) for i in invitation_service.for_candidate(db, c)]


@router.get("/invitations/{inv_id}", response_model=InvitationOut, responses=errors(404),
            summary="Открыть приглашение (статус → «просмотрено»)")
def open_invitation(inv_id: int, c: Candidate, db: DB):
    return presenters.invitation(invitation_service.open_for_candidate(db, c, inv_id), False)


@router.post("/invitations/{inv_id}/accept", response_model=InvitationOut, responses=errors(404, 409),
             summary="Принять приглашение — работодатель получит контакты")
def accept(inv_id: int, body: RespondIn, c: Candidate, db: DB):
    return presenters.invitation(invitation_service.respond(db, c, inv_id, True, body.message), False)


@router.post("/invitations/{inv_id}/reject", response_model=InvitationOut, responses=errors(404, 409),
             summary="Отклонить приглашение")
def reject(inv_id: int, body: RespondIn, c: Candidate, db: DB):
    return presenters.invitation(invitation_service.respond(db, c, inv_id, False, body.message), False)


@router.post("/invitations/{inv_id}/report", response_model=InvitationOut, responses=errors(404),
             summary="Пожаловаться на недобросовестное предложение")
def report(inv_id: int, body: ReportIn, c: Candidate, db: DB):
    return presenters.invitation(invitation_service.report(db, c, inv_id, body.reason), False)


# ------------------------------------------------------------------ regular tasks

@router.get("/tasks", response_model=list[TaskOut], summary="Короткие задания от работодателей")
def tasks(c: Candidate, db: DB):
    return tasks_service.for_candidate(db, c)


@router.post("/tasks/{task_id}/submit", response_model=Message, responses=errors(404, 409, 422),
             summary="Отправить решение или подход")
def submit_task(task_id: int, body: SubmissionIn, c: Candidate, db: DB):
    tasks_service.submit(db, c, task_id, body.answer)
    return Message(message=t("message.solution_sent"))
