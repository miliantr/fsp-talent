"""Matching engine: explainable multi-factor compatibility score "employer need ↔ candidate".

The engine is a pure function of plain data (no DB, no HTTP) so the very same code is used by the
API and by the offline benchmark (evaluation/evaluate_matching.py).

score = Σ_k w_k · s_k / Σ_k w_k   over *available* components k (each s_k ∈ [0, 1])

Key ideas that make it different from keyword search:
  * skills are matched through a skill graph (FastAPI ≈ Flask) and weighted by EVIDENCE —
    a declared skill confirmed by the candidate's test competency counts more than a claim;
  * competence is measured relative to the required grade on the comparable IRT scale;
  * the FSP signal has a neutral baseline: no history ≠ zero;
  * missing data (no salary expectation, no experience requirement) is "unavailable" and the
    weights are renormalised instead of silently penalising the candidate;
  * every component produces a human-readable reason.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime

from app.db.base import utcnow
from app.domain.catalog import GRADE_CUTS, GRADE_NAMES, GRADE_RANK, SPEC_NAMES, spec_similarity
from app.services.fsp.scoring import FSPSummary
from app.services.matching.config import (
    COMPONENT_LABELS,
    FRESHNESS_HALF_LIFE_DAYS,
    FSP_NEUTRAL,
    UNVERIFIED_SKILL_PRIOR,
    get_weights,
)

# ------------------------------------------------------------------ data


@dataclass
class SkillInfo:
    slug: str
    name: str
    competency_map: dict = field(default_factory=dict)
    related: dict = field(default_factory=dict)


class SkillGraph:
    def __init__(self, skills: list[SkillInfo]):
        self.skills = {s.slug: s for s in skills}

    def name(self, slug: str) -> str:
        s = self.skills.get(slug)
        return s.name if s else slug

    def similarity(self, have: str, need: str) -> float:
        if have == need:
            return 1.0
        h, n = self.skills.get(have), self.skills.get(need)
        return max(h.related.get(need, 0.0) if h else 0.0, n.related.get(have, 0.0) if n else 0.0)

    def competency(self, slug: str, specialization: str) -> str | None:
        s = self.skills.get(slug)
        return s.competency_map.get(specialization) if s else None


@dataclass
class CandidateFeatures:
    id: int
    specialization: str
    grade: str
    theta: float
    scaled_score: int
    confidence: float
    competency_scores: dict[str, int]
    skills: dict[str, int]                      # slug -> declared level 1..5
    experience_years: float = 0.0
    expected_salary: int | None = None
    work_format: str = "any"
    city: str | None = None
    fsp: FSPSummary | None = None               # summary relative to the job specialization
    last_active_at: datetime | None = None
    verified_at: datetime | None = None
    upgrade_eligible: bool = False
    fsp_by_spec: dict[str, FSPSummary] = field(default_factory=dict)


@dataclass
class JobFeatures:
    id: int
    specialization: str
    grade: str
    must_skills: list[str]
    nice_skills: list[str] = field(default_factory=list)
    salary_from: int | None = None
    salary_to: int | None = None
    work_format: str = "any"
    city: str | None = None
    min_experience_years: float = 0.0
    weights_preset: str = "balanced"


@dataclass
class Component:
    key: str
    value: float
    weight: float
    available: bool
    detail: str
    contribution: float = 0.0  # points of the final 0..100 score

    def to_dict(self) -> dict:
        return {
            "key": self.key, "label": COMPONENT_LABELS[self.key], "value": round(self.value, 3),
            "weight": round(self.weight, 3), "available": self.available, "detail": self.detail,
            "contribution": round(self.contribution, 1),
        }


@dataclass
class Reason:
    kind: str  # positive | neutral | negative
    component: str
    text: str

    def to_dict(self) -> dict:
        return {"kind": self.kind, "component": self.component, "text": self.text}


@dataclass
class SkillMatch:
    skill: str
    name: str
    importance: str
    status: str            # exact | related | missing
    via: str | None        # candidate skill used
    verified: bool         # confirmed by a test competency
    value: float

    def to_dict(self) -> dict:
        return self.__dict__ | {"value": round(self.value, 3)}


@dataclass
class MatchScore:
    candidate_id: int
    score: float
    components: dict[str, Component]
    reasons: list[Reason]
    skill_matches: list[SkillMatch]
    must_gate: float = 1.0

    @property
    def percent(self) -> int:
        return round(self.score * 100)

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 4),
            "percent": self.percent,
            "components": [c.to_dict() for c in self.components.values()],
            "reasons": [r.to_dict() for r in self.reasons],
            "skill_matches": [s.to_dict() for s in self.skill_matches],
            "must_gate": round(self.must_gate, 3),
        }


# ------------------------------------------------------------------ components

# must-have gate: gate = floor + (1 - floor) * must_coverage, normalised so that a typical fully
# covered stack (evidence ≈ 0.85) is not penalised at all.
MUST_GATE_FLOOR = 0.8
# How strongly test competency scores modulate trust in a declared skill (0 = ignore the test).
EVIDENCE_STRENGTH = 0.25
# Share of competency scores (vs overall ability) inside the test component.
TEST_COMPETENCY_SHARE = 0.35
MUST_GATE_FULL = 0.92

FORMAT_NAMES = {"remote": "удалённо", "office": "офис", "hybrid": "гибрид", "any": "любой"}


def _lower_first(s: str) -> str:
    """'Достижения ФСП' -> 'достижения ФСП' (keeps abbreviations intact)."""
    return s[:1].lower() + s[1:]


GRADE_FIT = {0: 1.0, 1: 0.6, -1: 0.4}  # |diff| >= 2 is excluded by the hard gate
FORMAT_FIT = {
    "remote": {"remote": 1.0, "office": 0.75, "hybrid": 0.9, "any": 1.0},
    "office": {"remote": 0.2, "office": 1.0, "hybrid": 0.7, "any": 1.0},
    "hybrid": {"remote": 0.5, "office": 0.9, "hybrid": 1.0, "any": 1.0},
    "any": {"remote": 1.0, "office": 1.0, "hybrid": 1.0, "any": 1.0},
}


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def skill_evidence(c: CandidateFeatures, slug: str, graph: SkillGraph) -> tuple[float, bool]:
    """How much we trust that the candidate really has the skill: declared level × test evidence."""
    level = c.skills.get(slug, 3)
    declared = min(1.0, 0.55 + 0.09 * level)
    comp = graph.competency(slug, c.specialization)
    if comp and comp in c.competency_scores:
        v = c.competency_scores[comp] / 100
        return declared * ((1 - EVIDENCE_STRENGTH) + EVIDENCE_STRENGTH * v), v >= 0.6
    return declared * ((1 - EVIDENCE_STRENGTH) + EVIDENCE_STRENGTH * UNVERIFIED_SKILL_PRIOR), False


def match_skill(c: CandidateFeatures, need: str, importance: str, graph: SkillGraph) -> SkillMatch:
    best, best_via, best_ver = 0.0, None, False
    for have in c.skills:
        sim = graph.similarity(have, need)
        if sim <= 0:
            continue
        ev, ver = skill_evidence(c, have, graph)
        if sim * ev > best:
            best, best_via, best_ver = sim * ev, have, ver
    status = "missing" if best_via is None else ("exact" if best_via == need else "related")
    return SkillMatch(need, graph.name(need), importance, status,
                      graph.name(best_via) if best_via else None, best_ver, best)


def _skills_component(c, job, graph):
    must = [match_skill(c, s, "must", graph) for s in job.must_skills]
    nice = [match_skill(c, s, "nice", graph) for s in job.nice_skills]
    if not must and not nice:
        return Component("skills", 0, 0, False, "Стек не указан"), []
    must_cov = sum(m.value for m in must) / len(must) if must else None
    nice_cov = sum(m.value for m in nice) / len(nice) if nice else None
    if must_cov is not None and nice_cov is not None:
        value = 0.75 * must_cov + 0.25 * nice_cov
    else:
        value = must_cov if must_cov is not None else nice_cov
    have = sum(1 for m in must if m.status != "missing")
    detail = f"{have} из {len(must)} обязательных" if must else f"{len(nice)} желательных"
    return Component("skills", value, 0, True, detail), must + nice


def _test_component(c, job, graph):
    # ability relative to the required level, capped at the next grade: over-qualification is
    # handled by the grade component and must not be rewarded twice
    ability = _sigmoid(1.7 * (min(c.theta, GRADE_CUTS[job.grade] + 1.0) - GRADE_CUTS[job.grade]))
    comps = {graph.competency(s, job.specialization) for s in job.must_skills + job.nice_skills}
    rel = [c.competency_scores[k] / 100 for k in comps if k and k in c.competency_scores]
    if rel:
        value = (1 - TEST_COMPETENCY_SHARE) * ability + TEST_COMPETENCY_SHARE * (sum(rel) / len(rel))
    else:
        value = ability
    return Component("test", value, 0, True,
                     f"{c.scaled_score}/100, уверенность {round(c.confidence * 100)}%")


def _grade_component(c, job):
    diff = GRADE_RANK[c.grade] - GRADE_RANK[job.grade]
    value = GRADE_FIT.get(diff, 0.0)
    if diff == -1 and c.upgrade_eligible:
        value = 0.6
    return Component("grade", value, 0, True, f"{GRADE_NAMES[c.grade]} vs {GRADE_NAMES[job.grade]}")


def _fsp_component(fsp: FSPSummary | None):
    if not fsp or not fsp.available:
        return Component("fsp", FSP_NEUTRAL, 0, True, "нет истории — нейтральная база")
    value = FSP_NEUTRAL + (1 - FSP_NEUTRAL) * fsp.strength
    return Component("fsp", value, 0, True, f"{fsp.count} достиж., сила {round(fsp.strength * 100)}%")


def _freshness_component(c, now: datetime):
    stamps = [t for t in (c.last_active_at, c.verified_at) if t]
    if not stamps:
        return Component("freshness", 0.5, 0, True, "нет данных"), None
    days = max(0, (now - max(stamps)).days)
    return Component("freshness", 0.5 ** (days / FRESHNESS_HALF_LIFE_DAYS), 0, True,
                     "сегодня" if days == 0 else f"{days} дн. назад"), days


def _salary_component(c, job):
    if not c.expected_salary or not job.salary_to:
        return Component("salary", 0, 0, False, "ожидания не указаны")
    if c.expected_salary <= job.salary_to:
        return Component("salary", 1.0, 0, True, "в вилке")
    over = (c.expected_salary - job.salary_to) / job.salary_to
    return Component("salary", max(0.0, 1 - over * 2.5), 0, True, f"выше вилки на {round(over * 100)}%")


def _experience_component(c, job):
    if job.min_experience_years <= 0:
        return Component("experience", 0, 0, False, "не требуется")
    return Component("experience", min(1.0, c.experience_years / job.min_experience_years), 0, True,
                     f"{c.experience_years:g} из {job.min_experience_years:g} лет")


def _format_component(c, job):
    value = FORMAT_FIT.get(job.work_format, FORMAT_FIT["any"]).get(c.work_format, 1.0)
    detail = f"{FORMAT_NAMES.get(c.work_format, c.work_format)} / {FORMAT_NAMES.get(job.work_format, job.work_format)}"
    if job.work_format in ("office", "hybrid") and c.work_format != "remote" and job.city and c.city \
            and job.city.lower() != c.city.lower():
        value *= 0.7
        detail += f", другой город ({c.city})"
    return Component("format", value, 0, True, detail)


# ------------------------------------------------------------------ public API


def is_eligible(c: CandidateFeatures, job: JobFeatures) -> bool:
    """Hard gates: unrelated specialization or a grade gap of two levels (either direction)."""
    if spec_similarity(c.specialization, job.specialization) <= 0:
        return False
    return abs(GRADE_RANK[c.grade] - GRADE_RANK[job.grade]) < 2


def score_candidate(c: CandidateFeatures, job: JobFeatures, graph: SkillGraph,
                    now: datetime | None = None, weights: dict[str, float] | None = None) -> MatchScore:
    now = now or utcnow()
    weights = weights or get_weights(job.weights_preset)
    fsp = c.fsp_by_spec.get(job.specialization, c.fsp)

    spec_val = spec_similarity(c.specialization, job.specialization)
    skills, skill_matches = _skills_component(c, job, graph)
    fresh, days = _freshness_component(c, now)
    comps = {
        "skills": skills,
        "test": _test_component(c, job, graph),
        "grade": _grade_component(c, job),
        "specialization": Component("specialization", spec_val, 0, True,
                                    SPEC_NAMES.get(c.specialization, c.specialization)),
        "fsp": _fsp_component(fsp),
        "freshness": fresh,
        "salary": _salary_component(c, job),
        "experience": _experience_component(c, job),
        "format": _format_component(c, job),
    }
    # "Soft AND" for must-have skills: missing required skills scale the whole score down, so strong
    # test/grade signals cannot mask the absence of what the employer explicitly requires.
    must = [m for m in skill_matches if m.importance == "must"]
    gate = MUST_GATE_FLOOR + (1 - MUST_GATE_FLOOR) * (sum(m.value for m in must) / len(must)) if must else 1.0
    gate = min(1.0, gate / MUST_GATE_FULL) if must else 1.0

    total_w = sum(weights[k] for k, comp in comps.items() if comp.available)
    score = 0.0
    for k, comp in comps.items():
        comp.weight = weights[k] / total_w if comp.available else 0.0
        comp.contribution = 100 * comp.weight * comp.value * gate
        score += comp.weight * comp.value * gate

    reasons = _reasons(c, job, comps, skill_matches, fsp, days)
    if gate < 0.9:
        reasons.append(Reason("negative", "skills",
                              f"Не хватает обязательных навыков: итог умножен на {gate:.2f}"))
    return MatchScore(c.id, score, comps, reasons, skill_matches, gate)


def rank(candidates: list[CandidateFeatures], job: JobFeatures, graph: SkillGraph,
         now: datetime | None = None) -> list[MatchScore]:
    now = now or utcnow()
    weights = get_weights(job.weights_preset)
    by_id = {c.id: c for c in candidates}
    scored = [score_candidate(c, job, graph, now, weights) for c in candidates if is_eligible(c, job)]
    # ties: stronger verified ability first, then FSP strength
    scored.sort(key=lambda m: (-round(m.score, 4), -by_id[m.candidate_id].theta,
                               -m.components["fsp"].value))
    return scored


def profile_strength(c: CandidateFeatures, now: datetime | None = None) -> float:
    """Strength of the verified profile inside its own category (no employer need given):
    ability above the grade cut-point, FSP record (neutral baseline) and freshness."""
    now = now or utcnow()
    ability = _sigmoid(1.7 * (c.theta - GRADE_CUTS[c.grade]))
    fsp = _fsp_component(c.fsp_by_spec.get(c.specialization, c.fsp)).value
    fresh, _ = _freshness_component(c, now)
    return 0.6 * ability + 0.25 * fsp + 0.15 * fresh.value


def compare(a: MatchScore, b: MatchScore) -> dict:
    """Why A is ranked above B: per-component difference in score points."""
    deltas = []
    for k, ca in a.components.items():
        cb = b.components[k]
        d = ca.contribution - cb.contribution
        if abs(d) >= 0.05:
            deltas.append({"key": k, "label": COMPONENT_LABELS[k], "delta": round(d, 1)})
    deltas.sort(key=lambda x: -abs(x["delta"]))
    plus = [d for d in deltas if d["delta"] > 0][:3]
    minus = [d for d in deltas if d["delta"] < 0][:2]
    text = f"Разница {a.percent - b.percent:+d} п."
    if plus:
        text += " Преимущество: " + ", ".join(f"{_lower_first(d['label'])} ({d['delta']:+.1f})" for d in plus) + "."
    if minus:
        text += " Уступает: " + ", ".join(f"{_lower_first(d['label'])} ({d['delta']:+.1f})" for d in minus) + "."
    return {"delta_percent": a.percent - b.percent, "components": deltas, "summary": text}


# ------------------------------------------------------------------ explanations


def plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _rub(x: int) -> str:
    return f"{x:,}".replace(",", " ") + " ₽"


def _reasons(c: CandidateFeatures, job: JobFeatures, comps: dict[str, Component],
             skills: list[SkillMatch], fsp: FSPSummary | None, days: int | None) -> list[Reason]:
    out: list[Reason] = []
    spec = comps["specialization"].value
    if spec >= 1:
        out.append(Reason("positive", "specialization",
                          f"Специализация {SPEC_NAMES[job.specialization]} совпадает"))
    else:
        out.append(Reason("neutral", "specialization",
                          f"Смежная специализация: {SPEC_NAMES[c.specialization]}"))

    diff = GRADE_RANK[c.grade] - GRADE_RANK[job.grade]
    if diff == 0:
        out.append(Reason("positive", "grade", f"Подтверждённый грейд {GRADE_NAMES[c.grade]} — как требуется"))
    elif diff > 0:
        out.append(Reason("neutral", "grade", f"Грейд выше требуемого: {GRADE_NAMES[c.grade]}"))
    elif c.upgrade_eligible:
        out.append(Reason("neutral", "grade",
                          f"Грейд {GRADE_NAMES[c.grade]}, но тест показал готовность к повышению"))
    else:
        out.append(Reason("negative", "grade", f"Грейд ниже требуемого: {GRADE_NAMES[c.grade]}"))

    if comps["skills"].available:
        must = [s for s in skills if s.importance == "must"]
        pct = round(comps["skills"].value * 100)
        verified = sum(1 for s in skills if s.verified and s.status != "missing")
        kind = "positive" if pct >= 70 else ("neutral" if pct >= 45 else "negative")
        txt = f"Совместимость стека {pct}%"
        if must:
            txt += f": {sum(1 for s in must if s.status != 'missing')} из {len(must)} обязательных навыков"
        if verified:
            txt += f", {verified} подтверждены тестом"
        out.append(Reason(kind, "skills", txt))
        related = [s for s in skills if s.status == "related"]
        if related:
            out.append(Reason("neutral", "skills", "Близкие навыки: " + ", ".join(
                f"{s.via} вместо {s.name}" for s in related[:3])))
        missing = [s.name for s in must if s.status == "missing"]
        if missing:
            out.append(Reason("negative", "skills", "Нет обязательных навыков: " + ", ".join(missing[:4])))

    t = comps["test"]
    out.append(Reason("positive" if t.value >= 0.6 else ("neutral" if t.value >= 0.4 else "negative"),
                      "test", f"Тест: {c.scaled_score}/100 (уверенность {round(c.confidence * 100)}%)"))

    if fsp and fsp.available:
        txt = f"{fsp.count} {plural(fsp.count, 'подтверждённое достижение', 'подтверждённых достижения', 'подтверждённых достижений')} ФСП"
        if fsp.best_text:
            txt += f": {fsp.best_text}"
        out.append(Reason("positive", "fsp", txt))
    else:
        out.append(Reason("neutral", "fsp", "Нет истории ФСП — сигнал не учитывается, без штрафа"))

    if days is not None:
        if days <= 30:
            out.append(Reason("positive", "freshness", "Профиль активен сегодня" if days == 0 else
                              f"Профиль активен: {days} дн. назад"))
        elif days > 180:
            out.append(Reason("negative", "freshness", f"Профиль давно не обновлялся ({days} дн.)"))

    if comps["salary"].available and c.expected_salary:
        if comps["salary"].value >= 1:
            out.append(Reason("positive", "salary", f"Ожидания {_rub(c.expected_salary)} — в вилке"))
        else:
            out.append(Reason("negative", "salary",
                              f"Ожидания {_rub(c.expected_salary)} — {comps['salary'].detail}"))
    if comps["experience"].available and comps["experience"].value < 1:
        out.append(Reason("negative", "experience", f"Опыт {c.experience_years:g} г. при требуемых "
                                                    f"{job.min_experience_years:g}"))
    if comps["format"].value < 0.5:
        out.append(Reason("negative", "format", "Формат работы не совпадает"))

    order = {"positive": 0, "neutral": 1, "negative": 2}
    out.sort(key=lambda r: order[r.kind])
    return out

