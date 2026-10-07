"""Data access for candidate profiles (eager loading tuned for ranking whole categories)."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import CandidateCategory, CandidateProfile, CandidateSkill, FSPProfile, User


def _base():
    return (
        select(CandidateProfile)
        .join(User, User.id == CandidateProfile.user_id)
        .options(
            joinedload(CandidateProfile.user),
            selectinload(CandidateProfile.skills).joinedload(CandidateSkill.skill),
            selectinload(CandidateProfile.fsp_profile).selectinload(FSPProfile.achievements),
        )
    )


def searchable(db: Session, specializations: list[str] | None = None) -> list[CandidateProfile]:
    """Verified candidates who are open to offers and consented to publication."""
    q = _base().where(
        CandidateProfile.verified_grade_id.is_not(None),
        CandidateProfile.open_to_offers.is_(True),
        CandidateProfile.consent_publication_at.is_not(None),
        User.is_active.is_(True),
    )
    if specializations:  # any of the candidate's categories (one per specialization)
        q = q.where(CandidateProfile.categories.any(CandidateCategory.specialization_id.in_(specializations)))
    return list(db.scalars(q).unique())


def get_with_relations(db: Session, candidate_id: int) -> CandidateProfile | None:
    return db.scalars(_base().where(CandidateProfile.id == candidate_id)).unique().one_or_none()
