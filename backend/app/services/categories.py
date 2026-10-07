"""Candidate categories «specialization · grade».

A candidate may be verified in several specializations (Backend · Middle and DevOps · Junior):
one category per specialization, one of them primary. The profile columns `verified_*` mirror the
primary category; matching picks the category that fits the requirement's specialization.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.domain.catalog import GRADE_RANK, spec_similarity
from app.i18n import t
from app.models import AttemptStatus, CandidateCategory, CandidateProfile, TestAttempt


def get(c: CandidateProfile, specialization: str | None) -> CandidateCategory | None:
    return next((k for k in c.categories if k.specialization_id == specialization), None)


def primary(c: CandidateProfile) -> CandidateCategory | None:
    return next((k for k in c.categories if k.is_primary), None)


def for_spec(c: CandidateProfile, specialization: str | None) -> CandidateCategory | None:
    """The category that represents the candidate for a requirement: the same specialization, else the
    closest one (spec similarity), else the primary category."""
    if not c.categories:
        return None
    if specialization:
        exact = get(c, specialization)
        if exact:
            return exact
        best = max(c.categories, key=lambda k: (spec_similarity(k.specialization_id, specialization), k.is_primary))
        if spec_similarity(best.specialization_id, specialization) > 0:
            return best
    return primary(c) or c.categories[0]


def sync_primary(c: CandidateProfile) -> None:
    """Mirror the primary category into the profile columns (or clear them)."""
    p = primary(c)
    if p is None and c.categories:
        p = c.categories[0]
        p.is_primary = True
    if p is None:
        c.verified_specialization_id = c.verified_grade_id = None
        c.verified_at = c.grade_locked_until = None
        c.ability_theta = c.scaled_score = c.category_confidence = None
        c.competency_scores = {}
        c.upgrade_eligible = False
        return
    c.verified_specialization_id, c.verified_grade_id = p.specialization_id, p.grade_id
    c.verified_at, c.grade_locked_until, c.upgrade_eligible = p.verified_at, p.grade_locked_until, p.upgrade_eligible
    c.ability_theta, c.scaled_score = p.theta, p.scaled_score
    c.category_confidence, c.competency_scores = p.confidence, dict(p.competency_scores or {})


def ensure(c: CandidateProfile, specialization: str, now: datetime) -> CandidateCategory:
    """The category of a specialization, created (unverified fields empty) when missing."""
    cat = get(c, specialization)
    if cat is None:
        cat = CandidateCategory(specialization_id=specialization, grade_id="junior", verified_at=now,
                                is_primary=not c.categories, competency_scores={})
        c.categories.append(cat)
    return cat


def set_primary(db: Session, c: CandidateProfile, specialization: str) -> None:
    cat = get(c, specialization)
    if cat is None:
        raise NotFound(t("error.category_not_found"))
    for k in c.categories:
        k.is_primary = k is cat
    sync_primary(c)
    db.commit()


def grade_status(db: Session, c: CandidateProfile) -> dict:
    """Self-declared grade vs the grade confirmed by the test (the grade is a skill level that only
    the test confirms; years of experience stay a profile attribute).

    status: confirmed | confirmed_lower | not_confirmed (tested, not passed) | not_tested | no_claim
    """
    spec, declared = c.specialization_id, c.declared_grade_id
    if not spec or not declared:
        return {"status": "no_claim", "specialization_id": spec, "declared_grade_id": declared,
                "confirmed_grade_id": None}
    cat = get(c, spec)
    if cat:
        status = "confirmed" if GRADE_RANK[cat.grade_id] >= GRADE_RANK[declared] else "confirmed_lower"
    else:
        tested = db.scalar(select(TestAttempt.id).where(
            TestAttempt.candidate_id == c.id, TestAttempt.specialization_id == spec,
            TestAttempt.status != AttemptStatus.IN_PROGRESS).limit(1))
        status = "not_confirmed" if tested else "not_tested"
    return {"status": status, "specialization_id": spec, "declared_grade_id": declared,
            "confirmed_grade_id": cat.grade_id if cat else None}
