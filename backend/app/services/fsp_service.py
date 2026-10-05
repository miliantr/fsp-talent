"""Linking a candidate with an FSP participant and syncing the achievements snapshot."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.security import hash_code, new_email_code
from app.db.base import utcnow
from app.i18n import t
from app.models import CandidateProfile, FSPAchievement, FSPProfile
from app.services.fsp.registry import RegistryParticipant, get_registry
from app.services.fsp.scoring import AchievementLike, FSPSummary, summarize
from app.services.mailer import send_email


def _mask(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:1]}{'*' * max(1, len(name) - 2)}{name[-1:]}@{domain}"


def _store(db: Session, profile: CandidateProfile, p: RegistryParticipant, source: str) -> FSPProfile:
    if profile.fsp_profile:
        db.delete(profile.fsp_profile)
        db.flush()
    fp = FSPProfile(candidate_id=profile.id, fsp_id=p.fsp_id, full_name=p.full_name, region=p.region,
                    sport_rank=p.sport_rank, source=source, synced_at=utcnow())
    for a in p.achievements:
        fp.achievements.append(FSPAchievement(
            external_id=a.id, event_name=a.event_name, discipline=a.discipline, level=a.level,
            date=a.date, place=a.place, participants_total=a.participants_total, team_name=a.team_name,
            role=a.role, score=a.score, specialization_hint=a.specialization_hint,
            certificate_url=a.certificate_url,
        ))
    db.add(fp)
    profile.fsp_id = p.fsp_id
    profile.fsp_pending_id = profile.fsp_code_hash = profile.fsp_code_expires_at = None
    profile.profile_updated_at = utcnow()
    db.flush()
    db.refresh(profile)
    return fp


def _claimed_by_other(db: Session, profile: CandidateProfile, fsp_id: str) -> bool:
    other = db.query(CandidateProfile).filter(CandidateProfile.fsp_id == fsp_id,
                                              CandidateProfile.id != profile.id).first()
    return other is not None


def try_auto_link(db: Session, profile: CandidateProfile) -> bool:
    """Enrich the profile automatically when the verified e-mail is known to the FSP registry."""
    if profile.fsp_id:
        return True
    registry = get_registry()
    try:
        p = registry.find_by_email(profile.user.email)
    except Exception:  # registry outage must never break registration
        return False
    if not p or _claimed_by_other(db, profile, p.fsp_id):
        return False
    _store(db, profile, p, registry.source)
    return True


def request_link(db: Session, profile: CandidateProfile, fsp_id: str) -> dict:
    fsp_id = fsp_id.strip().upper()
    registry = get_registry()
    p = registry.get_participant(fsp_id)
    if not p:
        raise NotFound(t("error.fsp_not_found"), code="fsp_not_found")
    if _claimed_by_other(db, profile, p.fsp_id):
        raise Conflict(t("error.fsp_taken"), code="fsp_taken")
    if p.email and p.email.lower() == profile.user.email.lower():
        _store(db, profile, p, registry.source)
        db.commit()
        return {"status": "linked", "masked_email": None, "dev_code": None}
    # ownership must be confirmed: one-time code to the e-mail registered in FSP
    # (with Keycloak-based FSP ID this step becomes "Sign in with FSP ID")
    code = new_email_code()
    profile.fsp_pending_id = p.fsp_id
    profile.fsp_code_hash = hash_code(code)
    profile.fsp_code_expires_at = utcnow() + timedelta(minutes=30)
    send_email(p.email, t("email.fsp_link.subject"), t("email.fsp_link.body", code=code))
    db.commit()
    return {
        "status": "confirmation_required",
        "masked_email": _mask(p.email) if p.email else None,
        "dev_code": code if get_settings().email_dev_expose_code else None,
    }


def confirm_link(db: Session, profile: CandidateProfile, code: str) -> None:
    if not profile.fsp_pending_id or not profile.fsp_code_hash:
        raise ValidationFailed(t("error.fsp_no_pending"))
    if not profile.fsp_code_expires_at or utcnow() > profile.fsp_code_expires_at:
        raise ValidationFailed(t("error.fsp_code_expired"), code="code_expired")
    if hash_code(code.strip()) != profile.fsp_code_hash:
        raise ValidationFailed(t("error.fsp_code_invalid"), code="code_invalid")
    registry = get_registry()
    p = registry.get_participant(profile.fsp_pending_id)
    if not p:
        raise NotFound(t("error.fsp_participant_missing"))
    if _claimed_by_other(db, profile, p.fsp_id):
        raise Conflict(t("error.fsp_taken"), code="fsp_taken")
    _store(db, profile, p, registry.source)
    db.commit()


def sync(db: Session, profile: CandidateProfile) -> None:
    if not profile.fsp_id:
        raise ValidationFailed(t("error.fsp_not_linked"))
    registry = get_registry()
    p = registry.get_participant(profile.fsp_id)
    if not p:
        raise NotFound(t("error.fsp_participant_gone"))
    _store(db, profile, p, registry.source)
    db.commit()


def unlink(db: Session, profile: CandidateProfile) -> None:
    if profile.fsp_profile:
        db.delete(profile.fsp_profile)
    profile.fsp_id = None
    db.commit()


def to_achievements(fp: FSPProfile | None) -> list[AchievementLike]:
    if not fp:
        return []
    return [AchievementLike(a.event_name, a.discipline, a.level, a.date, a.place, a.participants_total,
                            a.role, a.specialization_hint) for a in fp.achievements]


def summary_for(profile: CandidateProfile, specialization: str | None, today: date | None = None) -> FSPSummary:
    fp = profile.fsp_profile
    spec = specialization or profile.verified_specialization_id or profile.specialization_id or "backend"
    return summarize(to_achievements(fp), spec, today or utcnow().date(), fp.sport_rank if fp else None)
