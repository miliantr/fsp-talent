"""Matching workflow: DB → features → engine → persisted, filterable ranking snapshot."""

from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.db.base import utcnow
from app.domain.catalog import SPECIALIZATIONS, spec_similarity
from app.i18n import component_label, t
from app.models import (
    Application,
    CandidateProfile,
    EmployerProfile,
    Invitation,
    Job,
    MatchResult,
)
from app.repositories import candidates as cand_repo
from app.repositories.reference import skill_graph
from app.services import categories as category_service
from app.services import fsp_service, presenters, privacy
from app.services.fsp.scoring import summarize
from app.services.matching import engine
from app.services.matching.config import ENGINE_VERSION, get_weights
from app.services.testing import service as testing_service

SNAPSHOT_TTL = timedelta(minutes=5)
# Candidates below this compatibility are not part of the selection (noise for the employer).
MIN_MATCH_SCORE = 0.35


def candidate_features(c: CandidateProfile, today=None, specialization: str | None = None) -> engine.CandidateFeatures:
    """Features of the candidate as seen by a requirement of `specialization`: the category of that
    specialization (or the closest one) represents the candidate; other categories add skill evidence."""
    today = today or utcnow().date()
    by_spec = {}
    if c.show_fsp and c.fsp_profile:
        achs = fsp_service.to_achievements(c.fsp_profile)
        for s in SPECIALIZATIONS:
            by_spec[s["id"]] = summarize(achs, s["id"], today, c.fsp_profile.sport_rank)
    cat = category_service.for_spec(c, specialization)
    if cat is not None:
        spec, grade, theta, score = cat.specialization_id, cat.grade_id, cat.theta, cat.scaled_score
        conf, comps, verified_at, upgrade = cat.confidence, cat.competency_scores, cat.verified_at, cat.upgrade_eligible
    else:  # profile columns (rows created before categories were introduced)
        spec, grade, theta, score = c.verified_specialization_id, c.verified_grade_id, c.ability_theta, c.scaled_score
        conf, comps, verified_at, upgrade = c.category_confidence, c.competency_scores, c.verified_at, c.upgrade_eligible
    return engine.CandidateFeatures(
        id=c.id,
        specialization=spec,
        grade=grade,
        theta=theta or 0.0,
        scaled_score=score or 0,
        confidence=conf or 0.5,
        competency_scores=comps or {},
        skills={cs.skill.slug: cs.level for cs in c.skills},
        experience_years=c.experience_years or 0,
        expected_salary=c.expected_salary if c.show_salary else None,
        work_format=c.work_format,
        city=c.city,
        last_active_at=c.last_active_at,
        verified_at=verified_at,
        upgrade_eligible=upgrade,
        fsp_by_spec=by_spec,
        other_competencies={k.specialization_id: k.competency_scores or {} for k in c.categories
                            if k.specialization_id != spec},
    )


def job_features(j: Job) -> engine.JobFeatures:
    return engine.JobFeatures(
        id=j.id, specialization=j.specialization_id, grade=j.grade_id,
        must_skills=[s.skill.slug for s in j.skills if s.importance == "must"],
        nice_skills=[s.skill.slug for s in j.skills if s.importance == "nice"],
        salary_from=j.salary_from, salary_to=j.salary_to, work_format=j.work_format, city=j.city,
        min_experience_years=j.min_experience_years, weights_preset=j.weights_preset,
    )


def get_job(db: Session, employer: EmployerProfile, job_id: int) -> Job:
    j = db.get(Job, job_id)
    if not j or j.employer_id != employer.id:
        raise NotFound(t("error.requirement_not_found"))
    return j


def run(db: Session, job: Job, now: datetime | None = None) -> list[MatchResult]:
    """Recompute the ranking for a need and persist it (shortlist marks are preserved)."""
    now = now or utcnow()
    specs = [s["id"] for s in SPECIALIZATIONS if spec_similarity(s["id"], job.specialization_id) > 0]
    pool = cand_repo.searchable(db, specs)
    feats = [candidate_features(c, now.date(), job.specialization_id) for c in pool]
    ranked = [m for m in engine.rank(feats, job_features(job), skill_graph(), now) if m.score >= MIN_MATCH_SCORE]

    old = {m.candidate_id: m for m in db.scalars(select(MatchResult).where(MatchResult.job_id == job.id))}
    keep_ids = {m.candidate_id for m in ranked}
    db.execute(delete(MatchResult).where(MatchResult.job_id == job.id,
                                         MatchResult.candidate_id.not_in(keep_ids or {-1})))
    rows = []
    for pos, m in enumerate(ranked, start=1):
        d = m.to_dict()
        row = old.get(m.candidate_id)
        if row is None:
            row = MatchResult(job_id=job.id, candidate_id=m.candidate_id)
            db.add(row)
        row.score, row.rank, row.engine_version, row.computed_at = m.score, pos, ENGINE_VERSION, now
        row.components = {"components": d["components"], "skill_matches": d["skill_matches"],
                          "must_gate": d["must_gate"]}
        row.explanation = d["reasons"]
        rows.append(row)
    job.matched_at = now
    db.commit()
    return rows


def ensure_fresh(db: Session, job: Job) -> None:
    now = utcnow()
    if not job.matched_at or job.updated_at > job.matched_at or now - job.matched_at > SNAPSHOT_TTL:
        run(db, job, now)


def list_matches(db: Session, employer: EmployerProfile, job: Job, *, grades: list[str] | None = None,
                 has_fsp: bool | None = None, min_score: int | None = None, skills: list[str] | None = None,
                 categories: list[str] | None = None, shortlisted: bool | None = None,
                 limit: int = 50, offset: int = 0, refresh: bool = False) -> dict:
    if refresh:
        run(db, job)
    else:
        ensure_fresh(db, job)
    rows = list(db.scalars(select(MatchResult).where(MatchResult.job_id == job.id).order_by(MatchResult.rank)))
    profiles = {c.id: c for c in cand_repo.searchable(db)}
    rows = [r for r in rows if r.candidate_id in profiles]
    graph = skill_graph()

    invitations = {i.candidate_id: i.status for i in db.scalars(select(Invitation).where(
        Invitation.employer_id == employer.id).order_by(Invitation.created_at))}
    applied = set(db.scalars(select(Application.candidate_id).where(Application.job_id == job.id)))

    # categories are aggregated over the full ranking, so refining filters never loses the selection
    # the category that represents each candidate for this requirement (one per candidate)
    shown = {r.candidate_id: presenters.category(profiles[r.candidate_id], job.specialization_id) for r in rows}
    cat_stats: dict[str, dict] = {}
    for r in rows:
        k = shown[r.candidate_id]
        s = cat_stats.setdefault(k["label"], {"label": k["label"], "specialization_id": k["specialization_id"],
                                              "grade_id": k["grade_id"], "count": 0, "sum": 0.0, "top": 0})
        s["count"] += 1
        s["sum"] += r.score
        s["top"] = max(s["top"], round(r.score * 100))

    def keep(r: MatchResult) -> bool:
        c = profiles[r.candidate_id]
        if grades and shown[c.id]["grade_id"] not in grades:
            return False
        if categories and shown[c.id]["label"] not in categories:
            return False
        if has_fsp is not None and (bool(c.fsp_profile and c.fsp_profile.achievements and c.show_fsp) != has_fsp):
            return False
        if min_score is not None and round(r.score * 100) < min_score:
            return False
        if skills:
            have = {cs.skill.slug for cs in c.skills}
            if not set(skills) <= have:
                return False
        return not (shortlisted and not r.shortlisted)

    filtered = [r for r in rows if keep(r)]
    items = []
    for r in filtered[offset:offset + limit]:
        c = profiles[r.candidate_id]
        fsp = fsp_service.summary_for(c, job.specialization_id)
        card = presenters.candidate_card(c, graph, fsp, specialization=job.specialization_id)
        card.update({
            "match": presenters.match({
                "percent": round(r.score * 100), "rank": r.rank, "score": r.score,
                "components": r.components.get("components", []),
                "skill_matches": r.components.get("skill_matches", []), "reasons": r.explanation,
                "must_gate": r.components.get("must_gate", 1.0)}),
            "shortlisted": r.shortlisted,
            "invitation_status": invitations.get(c.id),
            "applied": c.id in applied,
        })
        items.append(card)

    weights = get_weights(job.weights_preset)
    return {
        "requirement": presenters.job(job),
        "total": len(rows),
        "filtered": len(filtered),
        "items": items,
        "categories": sorted(
            ({"label": s["label"], "specialization_id": s["specialization_id"], "grade_id": s["grade_id"],
              "count": s["count"], "avg_percent": round(100 * s["sum"] / s["count"]), "top_percent": s["top"]}
             for s in cat_stats.values()), key=lambda s: -s["avg_percent"]),
        "computed_at": job.matched_at,
        "engine_version": ENGINE_VERSION,
        "weights": [{"key": k, "label": component_label(k), "weight": round(v, 3)} for k, v in weights.items()],
    }


def set_shortlist(db: Session, job: Job, candidate_id: int, value: bool) -> None:
    row = db.scalar(select(MatchResult).where(MatchResult.job_id == job.id,
                                              MatchResult.candidate_id == candidate_id))
    if not row:
        raise NotFound(t("error.candidate_not_in_selection"))
    row.shortlisted = value
    db.commit()


def explain(db: Session, job: Job, candidate: CandidateProfile) -> engine.MatchScore | None:
    if not candidate.is_verified:
        return None
    # computed even for candidates outside the ranking gates, so any profile stays explainable
    return engine.score_candidate(candidate_features(candidate, specialization=job.specialization_id),
                                  job_features(job), skill_graph())


def compare(db: Session, job: Job, a: CandidateProfile, b: CandidateProfile) -> dict:
    ma, mb = explain(db, job, a), explain(db, job, b)
    if not ma or not mb:
        raise NotFound(t("error.compare_verified_only"))
    res = engine.compare(ma, mb)
    res["a"] = {"candidate_id": a.id, "percent": ma.percent,
                "components": [presenters.component(c.to_dict()) for c in ma.components.values()]}
    res["b"] = {"candidate_id": b.id, "percent": mb.percent,
                "components": [presenters.component(c.to_dict()) for c in mb.components.values()]}
    return res


def search_bank(db: Session, employer: EmployerProfile, *, specialization: str | None = None,
                grades: list[str] | None = None, skills: list[str] | None = None, has_fsp: bool | None = None,
                categories: list[str] | None = None, limit: int = 50, offset: int = 0) -> dict:
    """Browse the whole verified pool; inside a category candidates are ranked by profile strength."""
    pool = cand_repo.searchable(db, [specialization] if specialization else None)
    graph = skill_graph()
    now = utcnow()
    invitations = {i.candidate_id: i.status for i in db.scalars(select(Invitation).where(
        Invitation.employer_id == employer.id).order_by(Invitation.created_at))}
    rows = []
    cats: dict[str, int] = {}
    for c in pool:
        own = presenters.categories(c)
        for k in own:
            if not specialization or k["specialization_id"] == specialization:
                cats[k["label"]] = cats.get(k["label"], 0) + 1
        # the category shown on the card: the filtered one, else the specialization's, else the primary
        cat = next((k for k in own if k["label"] in categories), None) if categories else \
            presenters.category(c, specialization)
        if cat is None or (grades and cat["grade_id"] not in grades):
            continue
        fsp = fsp_service.summary_for(c, cat["specialization_id"])
        if has_fsp is not None and (fsp.available and c.show_fsp) != has_fsp:
            continue
        if skills:
            have = {cs.skill.slug for cs in c.skills}
            # skill graph aware: a close skill (Flask for FastAPI) counts as a partial hit
            if not all(any(graph.similarity(h, s) >= 0.6 for h in have) for s in skills):
                continue
        strength = engine.profile_strength(candidate_features(c, now.date(), cat["specialization_id"]), now)
        rows.append((strength, c, fsp, cat))
    rows.sort(key=lambda x: -x[0])
    items = []
    for strength, c, fsp, cat in rows[offset:offset + limit]:
        card = presenters.candidate_card(c, graph, fsp, specialization=cat["specialization_id"])
        card["profile_strength"] = round(strength * 100)
        card["invitation_status"] = invitations.get(c.id)
        items.append(card)
    return {"total": len(rows), "items": items,
            "categories": [{"label": k, "count": v} for k, v in sorted(cats.items())]}


def candidate_detail(db: Session, employer: EmployerProfile, candidate_id: int, job: Job | None) -> dict:
    c = cand_repo.get_with_relations(db, candidate_id)
    if not c or not (c.is_searchable or (c.is_verified and privacy.has_relationship(db, employer, c))):
        raise NotFound(t("error.candidate_hidden"))
    reason = privacy.contact_reason(db, employer, c)
    visible = reason is not None
    if visible:
        privacy.log_disclosure(db, employer.id, c.id, reason)
        db.commit()
    graph = skill_graph()
    spec = job.specialization_id if job else c.verified_specialization_id
    fsp = fsp_service.summary_for(c, spec)
    card = presenters.candidate_card(c, graph, fsp, contacts_visible=visible, specialization=spec)
    card["skills"] = presenters.skills(c, graph)
    history = [{"attempt_id": r.attempt_id, "target_grade": r.attempt.target_grade_id,
                "specialization_id": r.attempt.specialization_id, "outcome": r.outcome,
                "scaled_score": r.scaled_score, "created_at": r.created_at}
               for r in testing_service.results(db, c)]
    invs = db.scalars(select(Invitation).where(Invitation.employer_id == employer.id,
                                               Invitation.candidate_id == c.id).order_by(Invitation.created_at.desc()))
    match = explain(db, job, c) if job else None
    card.update({
        "about": c.about, "education": c.education, "team_roles": c.team_roles or [],
        "soft_skills": c.soft_skills or [],
        "competencies": presenters.competency_list(card["category"]["competency_scores"]
                                                   if card["category"] else {}),
        "test_history": history,
        "fsp_profile": presenters.fsp_profile(c.fsp_profile) if c.show_fsp else None,
        "contacts_visible": visible,
        "contacts_reason": reason,
        "contacts": privacy.contacts(c) if visible else None,
        "invitations": [presenters.invitation(i, True, privacy.contacts(c) if visible else None) for i in invs],
        "match": presenters.match(match.to_dict()) if match else None,
        "requirement_id": job.id if job else None,
    })
    return card
