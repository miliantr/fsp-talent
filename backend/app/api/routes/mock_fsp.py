"""Mock of the external FSP registry API (stands in for the real FSP service during the hackathon).

Contract consumed by HttpFSPRegistry:
  GET /participants/{fsp_id}          -> participant with achievements
  GET /participants?email=<e-mail>    -> participant or 404
"""

from fastapi import APIRouter, HTTPException

from app.services.fsp.registry import get_mock_registry

router = APIRouter(prefix="/mock-fsp/v1", tags=["Мок реестра ФСП"])


@router.get("/participants/{fsp_id}", summary="Участник ФСП по ФСП ID")
def participant(fsp_id: str):
    raw = get_mock_registry().raw_participant(fsp_id)
    if not raw:
        raise HTTPException(404, "participant not found")
    return raw


@router.get("/participants", summary="Поиск участника по e-mail")
def by_email(email: str):
    p = get_mock_registry().find_by_email(email)
    if not p:
        raise HTTPException(404, "participant not found")
    return get_mock_registry().raw_participant(p.fsp_id)


@router.get("/stats", summary="Сводка мок-реестра")
def stats():
    items = get_mock_registry().all_raw()
    return {"participants": len(items), "achievements": sum(len(p["achievements"]) for p in items)}
