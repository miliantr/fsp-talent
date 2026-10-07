"""Read models (plain dicts validated by response schemas). No business decisions here except
applying the privacy rules computed in services.privacy."""

from app.db.base import utcnow
from app.domain.catalog import GRADE_NAMES, GRADE_RANK, SPEC_NAMES
from app.i18n import competency_name, get_locale, has, render, skill_name, t
from app.models import (
    CandidateCategory,
    CandidateProfile,
    EmployerProfile,
    FSPProfile,
    Invitation,
    Job,
    TestAttempt,
    TestResult,
)
from app.services import categories as category_service
from app.services import privacy
from app.services.fsp.scoring import AchievementLike, FSPSummary, relevance, relevance_level
from app.services.testing.scoring import category_label, recommendation


def category_view(k: CandidateCategory) -> dict:
    return {
        "label": category_label(k.specialization_id, k.grade_id),
        "specialization_id": k.specialization_id,
        "specialization_name": SPEC_NAMES[k.specialization_id],
        "grade_id": k.grade_id,
        "grade_name": GRADE_NAMES[k.grade_id],
        "verified_at": k.verified_at,
        "scaled_score": k.scaled_score,
        "confidence": k.confidence,
        "theta": k.theta,
        "locked_until": k.grade_locked_until,
        "upgrade_eligible": k.upgrade_eligible,
        "is_primary": k.is_primary,
        "competency_scores": k.competency_scores or {},
    }


def category(c: CandidateProfile, specialization: str | None = None) -> dict | None:
    """The category representing the candidate: for a requirement of `specialization` — the category of
    that (or the closest) specialization; otherwise the primary one."""
    if not c.is_verified:
        return None
    k = category_service.for_spec(c, specialization)
    if k is not None:
        return category_view(k)
    return {  # profile columns (rows created before categories were introduced)
        "label": category_label(c.verified_specialization_id, c.verified_grade_id),
        "specialization_id": c.verified_specialization_id,
        "specialization_name": SPEC_NAMES[c.verified_specialization_id],
        "grade_id": c.verified_grade_id,
        "grade_name": GRADE_NAMES[c.verified_grade_id],
        "verified_at": c.verified_at,
        "scaled_score": c.scaled_score,
        "confidence": c.category_confidence,
        "theta": c.ability_theta,
        "locked_until": c.grade_locked_until,
        "upgrade_eligible": c.upgrade_eligible,
        "is_primary": True,
        "competency_scores": c.competency_scores or {},
    }


def declared(c: CandidateProfile) -> dict | None:
    """The grade the candidate claims in the survey; `confirmed` — the test confirmed it (or higher).
    Shown to an employer when an applicant has no verified category yet: «Backend · Middle — не подтверждён»."""
    if not c.specialization_id or not c.declared_grade_id:
        return None
    k = category_service.get(c, c.specialization_id)
    return {"label": category_label(c.specialization_id, c.declared_grade_id),
            "specialization_id": c.specialization_id, "grade_id": c.declared_grade_id,
            "confirmed": bool(k and GRADE_RANK[k.grade_id] >= GRADE_RANK[c.declared_grade_id])}


def categories(c: CandidateProfile) -> list[dict]:
    """All verified categories, the primary first."""
    if c.categories:
        return [category_view(k) for k in sorted(c.categories, key=lambda k: not k.is_primary)]
    one = category(c)
    return [one] if one else []


def competency_list(scores: dict) -> list[dict]:
    return [{"id": k, "name": competency_name(k), "score": v} for k, v in scores.items()]


def reason(r: dict) -> dict:
    """A stored explanation reason {kind, component, code, params} -> with text in the current locale
    (legacy rows that stored rendered text are passed through)."""
    return {"kind": r.get("kind", "neutral"), "component": r.get("component", ""), "text": render(r)}


def component(c: dict) -> dict:
    """A stored score component -> with the label and detail in the current locale."""
    detail = c.get("detail")
    return {**{k: v for k, v in c.items() if k != "detail_msg"},
            "label": t(f"ref.component.{c['key']}"),
            "detail": render(c["detail_msg"]) if c.get("detail_msg") else detail or ""}


def skill_match(s: dict) -> dict:
    return {**s, "name": skill_name(s["skill"]),
            "via": skill_name(s["via_slug"]) if s.get("via_slug") else s.get("via")}


def match(m: dict) -> dict:
    """A stored MatchScore.to_dict() snapshot -> localized view."""
    return {**m, "components": [component(c) for c in m.get("components", [])],
            "reasons": [reason(r) for r in m.get("reasons", [])],
            "skill_matches": [skill_match(s) for s in m.get("skill_matches", [])]}


def skills(c: CandidateProfile, graph) -> list[dict]:
    """Declared skills; a skill counts as confirmed when the competency that covers it was scored ≥ 60%
    in any of the candidate's verified categories."""
    tested = {k["specialization_id"]: k["competency_scores"] for k in categories(c)}
    out = []
    for cs in sorted(c.skills, key=lambda s: (-s.level, s.skill.name)):
        scores = [sc[comp] for spec, sc in tested.items()
                  if (comp := graph.competency(cs.skill.slug, spec)) and comp in sc]
        score = max(scores) if scores else None
        out.append({"slug": cs.skill.slug, "name": skill_name(cs.skill.slug), "level": cs.level, "years": cs.years,
                    "verified": score is not None and score >= 60, "competency_score": score})
    return out


def fsp_summary(s: FSPSummary) -> dict:
    return {"available": s.available, "strength": s.strength, "count": s.count, "prizes": s.prizes,
            "best_text": render(s.best) if s.best else None, "sport_rank": s.sport_rank,
            "highlights": [render(h) for h in s.highlights]}


def fsp_profile(fp: FSPProfile | None, specialization: str | None = None) -> dict | None:
    """The registry record; with a specialization every achievement carries the relevance of its
    discipline to it (core / adjacent / other) — the same rule the matching engine weights by."""
    if not fp:
        return None

    def rel(a) -> str | None:
        if not specialization:
            return None
        like = AchievementLike(a.event_name, a.discipline, a.level, a.date, a.place, a.participants_total,
                               a.role, a.specialization_hint)
        return relevance_level(relevance(like, specialization))

    return {
        "fsp_id": fp.fsp_id, "full_name": fp.full_name, "region": fp.region, "sport_rank": fp.sport_rank,
        "source": fp.source, "synced_at": fp.synced_at,
        "achievements": [{
            "id": a.external_id, "event_name": a.event_name, "discipline": a.discipline,
            "level": a.level, "level_name": t(f"fsp.level.{a.level}") if has(f"fsp.level.{a.level}") else a.level,
            "date": a.date,
            "place": a.place, "participants_total": a.participants_total, "team_name": a.team_name,
            "role": a.role, "score": a.score, "certificate_url": a.certificate_url, "relevance": rel(a),
        } for a in fp.achievements],
    }


def candidate_card(c: CandidateProfile, graph, fsp: FSPSummary, contacts_visible: bool = False,
                   specialization: str | None = None) -> dict:
    last = max([t for t in (c.last_active_at, c.verified_at) if t], default=None)
    return {
        "candidate_id": c.id,
        "display_name": privacy.display_name(c, contacts_visible),
        "headline": c.headline,
        "city": c.city,
        "experience_years": c.experience_years,
        "work_format": c.work_format,
        "expected_salary": c.expected_salary if c.show_salary else None,
        "category": category(c, specialization),
        "categories": categories(c),
        "declared": declared(c),
        "skills": skills(c, graph)[:8],
        "fsp": fsp_summary(fsp) if c.show_fsp else fsp_summary(FSPSummary(available=False)),
        "last_active_days": (utcnow() - last).days if last else None,
        "tasks": _tasks_signal(c),
    }


def _tasks_signal(c: CandidateProfile) -> dict | None:
    from app.services.tasks_service import signal  # tasks_service builds views with presenters

    return signal(c)


def company(e: EmployerProfile) -> dict:
    return {"id": e.id, "name": e.company_name or t("ref.company"), "industry": e.industry, "city": e.city,
            "website": e.website, "description": e.description, "size": e.size}


def job(j: Job) -> dict:
    return {
        "id": j.id, "title": j.title, "description": j.description, "team_description": j.team_description,
        "specialization_id": j.specialization_id, "specialization_name": SPEC_NAMES[j.specialization_id],
        "grade_id": j.grade_id, "grade_name": GRADE_NAMES[j.grade_id],
        "salary_from": j.salary_from, "salary_to": j.salary_to, "work_format": j.work_format,
        "city": j.city, "min_experience_years": j.min_experience_years, "weights_preset": j.weights_preset,
        "is_public": j.is_public, "status": j.status, "created_at": j.created_at, "updated_at": j.updated_at,
        "matched_at": j.matched_at,
        "skills": [{"slug": s.skill.slug, "name": skill_name(s.skill.slug), "importance": s.importance}
                   for s in sorted(j.skills, key=lambda s: (s.importance != "must", s.skill.name))],
        "company": company(j.employer),
    }


def invitation(inv: Invitation, for_employer: bool, contacts: dict | None = None) -> dict:
    c = inv.candidate
    return {
        "id": inv.id, "status": inv.status, "created_at": inv.created_at, "viewed_at": inv.viewed_at,
        "responded_at": inv.responded_at, "expires_at": inv.expires_at,
        "position_title": inv.position_title, "description": inv.description,
        "salary_from": inv.salary_from, "salary_to": inv.salary_to, "work_format": inv.work_format,
        "contact_method": inv.contact_method, "match_score": inv.match_score,
        "match_reasons": [reason(r) for r in inv.match_reasons or []], "candidate_message": inv.candidate_message,
        "job_id": inv.job_id, "job_title": inv.job.title if inv.job else None,
        "company": company(inv.employer),
        "candidate": {
            "id": c.id,
            "display_name": privacy.display_name(c, contacts is not None) if for_employer else
            f"{c.first_name} {c.last_name}".strip(),
            "category_label": category_label(c.verified_specialization_id, c.verified_grade_id)
            if c.is_verified else None,
        },
        "contacts": contacts,
    }


def _item_text(item) -> tuple[str, list]:
    """Question text and options in the current locale; the option order is the same in every
    language, so answers given in one language stay valid after switching."""
    tr = (item.i18n or {}).get(get_locale())
    return (tr["text"], tr["options"]) if tr else (item.text, item.options)


def attempt_view(att: TestAttempt, now) -> dict:
    return {
        "id": att.id, "specialization_id": att.specialization_id, "target_grade": att.target_grade_id,
        "status": att.status, "started_at": att.started_at, "deadline_at": att.deadline_at, "server_time": now,
        "answered": sum(1 for i in att.items if i.answer), "total": len(att.items), "blueprint": att.blueprint,
        "items": [{"id": i.id, "position": i.position, "competency_id": i.competency_id,
                   "competency_name": competency_name(i.competency_id), "qtype": i.qtype,
                   "text": _item_text(i)[0], "options": _item_text(i)[1],
                   "answer": i.answer.answer if i.answer else None}
                  for i in att.items],
    }


def result_view(r: TestResult) -> dict:
    att = r.attempt
    return {
        "attempt_id": r.attempt_id, "specialization_id": att.specialization_id, "target_grade": att.target_grade_id,
        "outcome": r.outcome, "passed": r.passed, "verified_grade": r.verified_grade_id,
        "category_label": r.category_label, "scaled_score": r.scaled_score, "raw_percent": r.raw_percent,
        "theta": r.theta, "theta_se": r.theta_se, "confidence": r.confidence,
        "competencies": competency_list(r.competency_scores or {}), "recommendation": recommendation(r.outcome, att.target_grade_id, att.status == "expired"),
        "grade_changed": r.grade_changed, "grade_change_blocked": r.grade_change_blocked,
        "upgrade_eligible": r.outcome == "passed_upgrade",
        "answered": sum(1 for i in att.items if i.answer), "total": len(att.items), "created_at": r.created_at,
    }
