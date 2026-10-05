"""Read models (plain dicts validated by response schemas). No business decisions here except
applying the privacy rules computed in services.privacy."""

from app.db.base import utcnow
from app.domain.catalog import GRADE_NAMES, SPEC_NAMES
from app.models import CandidateProfile, EmployerProfile, FSPProfile, Invitation, Job, TestAttempt, TestResult
from app.repositories.reference import COMPETENCY_NAMES
from app.services import privacy
from app.services.fsp.scoring import LEVEL_NAMES, FSPSummary
from app.services.testing.scoring import category_label


def category(c: CandidateProfile) -> dict | None:
    if not c.is_verified:
        return None
    return {
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
    }


def competency_list(scores: dict) -> list[dict]:
    return [{"id": k, "name": COMPETENCY_NAMES.get(k, k), "score": v} for k, v in scores.items()]


def skills(c: CandidateProfile, graph) -> list[dict]:
    out = []
    for cs in sorted(c.skills, key=lambda s: (-s.level, s.skill.name)):
        comp = graph.competency(cs.skill.slug, c.verified_specialization_id or c.specialization_id or "")
        score = c.competency_scores.get(comp) if comp and c.competency_scores else None
        out.append({"slug": cs.skill.slug, "name": cs.skill.name, "level": cs.level, "years": cs.years,
                    "verified": score is not None and score >= 60, "competency_score": score})
    return out


def fsp_summary(s: FSPSummary) -> dict:
    return {"available": s.available, "strength": s.strength, "count": s.count, "prizes": s.prizes,
            "best_text": s.best_text, "sport_rank": s.sport_rank, "highlights": s.highlights}


def fsp_profile(fp: FSPProfile | None) -> dict | None:
    if not fp:
        return None
    return {
        "fsp_id": fp.fsp_id, "full_name": fp.full_name, "region": fp.region, "sport_rank": fp.sport_rank,
        "source": fp.source, "synced_at": fp.synced_at,
        "achievements": [{
            "id": a.external_id, "event_name": a.event_name, "discipline": a.discipline,
            "level": a.level, "level_name": LEVEL_NAMES.get(a.level, a.level), "date": a.date,
            "place": a.place, "participants_total": a.participants_total, "team_name": a.team_name,
            "role": a.role, "score": a.score, "certificate_url": a.certificate_url,
        } for a in fp.achievements],
    }


def candidate_card(c: CandidateProfile, graph, fsp: FSPSummary, contacts_visible: bool = False) -> dict:
    last = max([t for t in (c.last_active_at, c.verified_at) if t], default=None)
    return {
        "candidate_id": c.id,
        "display_name": privacy.display_name(c, contacts_visible),
        "headline": c.headline,
        "city": c.city,
        "experience_years": c.experience_years,
        "work_format": c.work_format,
        "expected_salary": c.expected_salary if c.show_salary else None,
        "category": category(c),
        "skills": skills(c, graph)[:8],
        "fsp": fsp_summary(fsp) if c.show_fsp else fsp_summary(FSPSummary(available=False)),
        "last_active_days": (utcnow() - last).days if last else None,
    }


def company(e: EmployerProfile) -> dict:
    return {"id": e.id, "name": e.company_name or "Компания", "industry": e.industry, "city": e.city,
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
        "skills": [{"slug": s.skill.slug, "name": s.skill.name, "importance": s.importance}
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
        "match_reasons": inv.match_reasons or [], "candidate_message": inv.candidate_message,
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


def attempt_view(att: TestAttempt, now) -> dict:
    return {
        "id": att.id, "specialization_id": att.specialization_id, "target_grade": att.target_grade_id,
        "status": att.status, "started_at": att.started_at, "deadline_at": att.deadline_at, "server_time": now,
        "answered": sum(1 for i in att.items if i.answer), "total": len(att.items), "blueprint": att.blueprint,
        "items": [{"id": i.id, "position": i.position, "competency_id": i.competency_id,
                   "competency_name": COMPETENCY_NAMES.get(i.competency_id, i.competency_id), "qtype": i.qtype,
                   "text": i.text, "options": i.options, "answer": i.answer.answer if i.answer else None}
                  for i in att.items],
    }


def result_view(r: TestResult) -> dict:
    att = r.attempt
    return {
        "attempt_id": r.attempt_id, "specialization_id": att.specialization_id, "target_grade": att.target_grade_id,
        "outcome": r.outcome, "passed": r.passed, "verified_grade": r.verified_grade_id,
        "category_label": r.category_label, "scaled_score": r.scaled_score, "raw_percent": r.raw_percent,
        "theta": r.theta, "theta_se": r.theta_se, "confidence": r.confidence,
        "competencies": competency_list(r.competency_scores or {}), "recommendation": r.recommendation,
        "grade_changed": r.grade_changed, "grade_change_blocked": r.grade_change_blocked,
        "upgrade_eligible": r.outcome == "passed_upgrade",
        "answered": sum(1 for i in att.items if i.answer), "total": len(att.items), "created_at": r.created_at,
    }
