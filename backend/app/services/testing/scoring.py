"""Answer validation, item scoring and grade decision."""

import math
from dataclasses import dataclass

from app.domain.catalog import GRADE_BY_RANK, GRADE_CUTS, GRADE_NAMES, GRADE_RANK, SPEC_NAMES
from app.services.testing.irt import Posterior, eap, p_correct, scaled_score


class InvalidAnswer(ValueError):
    pass


def normalize_answer(qtype: str, n_options: int, answer: list) -> list:
    """Validates the raw answer payload for an item type and returns its canonical form."""
    if not isinstance(answer, list) or not answer:
        raise InvalidAnswer("Ответ не может быть пустым")
    if qtype == "numeric":
        if len(answer) != 1:
            raise InvalidAnswer("Ожидается одно число")
        try:
            value = float(str(answer[0]).replace(",", ".").replace(" ", ""))
        except ValueError as e:
            raise InvalidAnswer("Ответ должен быть числом") from e
        if not math.isfinite(value):
            raise InvalidAnswer("Ответ должен быть конечным числом")
        return [value]
    try:
        idx = sorted({int(x) for x in answer})
    except (TypeError, ValueError) as e:
        raise InvalidAnswer("Ожидаются номера вариантов ответа") from e
    if any(i < 0 or i >= n_options for i in idx):
        raise InvalidAnswer("Вариант ответа вне диапазона")
    if qtype == "single" and len(idx) != 1:
        raise InvalidAnswer("Нужно выбрать ровно один вариант")
    return idx


def score_answer(qtype: str, correct: list, answer: list | None) -> tuple[bool, float]:
    """Returns (is_correct for IRT, partial credit 0..1 for the competency profile)."""
    if not answer:
        return False, 0.0
    if qtype == "numeric":
        target = float(correct[0])
        ok = abs(float(answer[0]) - target) <= 1e-6 + 0.005 * abs(target)
        return ok, 1.0 if ok else 0.0
    if qtype == "single":
        ok = answer[0] in correct
        return ok, 1.0 if ok else 0.0
    right = set(correct)
    picked = set(answer)
    hits = len(right & picked)
    wrong = len(picked - right)
    credit = max(0.0, (hits - wrong) / len(right))
    return picked == right, credit


@dataclass
class GradedItem:
    competency: str
    a: float
    b: float
    c: float
    is_correct: bool
    credit: float
    is_family: bool = False  # parametric (leak-proof) item


@dataclass
class Outcome:
    theta: float
    theta_se: float
    scaled_score: int
    raw_percent: float
    passed: bool
    upgrade_eligible: bool
    outcome: str  # passed | passed_upgrade | not_passed
    confidence: float
    verified_grade: str | None
    competency_scores: dict[str, int]
    recommendation: str
    posterior: Posterior
    flagged: bool = False
    person_fit: float | None = None
    leak_z: float | None = None


def category_label(specialization: str, grade: str | None) -> str | None:
    if not grade:
        return None
    return f"{SPEC_NAMES.get(specialization, specialization)} · {GRADE_NAMES.get(grade, grade)}"


def person_fit_lz(items: list[GradedItem], theta: float) -> float | None:
    """Standardised log-likelihood lz of the response pattern (Drasgow et al., 1985).
    Strongly negative values = aberrant pattern, e.g. hard items right and easy items wrong."""
    l0 = e = v = 0.0
    for it in items:
        p = min(max(p_correct(theta, it.a, it.b, it.c), 1e-6), 1 - 1e-6)
        q = 1 - p
        l0 += math.log(p) if it.is_correct else math.log(q)
        e += p * math.log(p) + q * math.log(q)
        v += p * q * math.log(p / q) ** 2
    return (l0 - e) / math.sqrt(v) if v > 0 else None


def leak_gap_z(items: list[GradedItem]) -> float | None:
    """Ability on leak-prone (static) items minus ability on leak-proof (parametric) items, in SE.
    An honest candidate shows the same ability on both; memorised answers inflate only the former."""
    static = [(i.a, i.b, i.c, i.is_correct) for i in items if not i.is_family]
    fam = [(i.a, i.b, i.c, i.is_correct) for i in items if i.is_family]
    if len(fam) < 3 or len(static) < 5:
        return None
    ps, pf = eap(static), eap(fam)
    return (ps.theta - pf.theta) / math.sqrt(ps.se ** 2 + pf.se ** 2)


LZ_THRESHOLD = -2.0
LEAK_Z_THRESHOLD = 1.9

# Decision thresholds on the posterior probability.
PASS_PROBABILITY = 0.5      # P(θ ≥ cut of target grade)
UPGRADE_PROBABILITY = 0.8   # P(θ ≥ cut of the next grade) — "confident" overperformance


def grade_attempt(items: list[GradedItem], target_grade: str) -> Outcome:
    post = eap([(i.a, i.b, i.c, i.is_correct) for i in items])
    p_target = post.p_above(GRADE_CUTS[target_grade])
    passed = p_target >= PASS_PROBABILITY
    next_grade = GRADE_BY_RANK.get(GRADE_RANK[target_grade] + 1)
    lower_grade = GRADE_BY_RANK.get(GRADE_RANK[target_grade] - 1)
    upgrade = passed and next_grade is not None and post.p_above(GRADE_CUTS[next_grade]) >= UPGRADE_PROBABILITY

    comp_credit: dict[str, list[float]] = {}
    for it in items:
        comp_credit.setdefault(it.competency, []).append(it.credit)
    competency_scores = {c: round(100 * sum(v) / len(v)) for c, v in comp_credit.items()}
    raw = 100 * sum(i.credit for i in items) / max(1, len(items))

    lz = person_fit_lz(items, post.theta)
    gap = leak_gap_z(items)
    flagged = passed and ((lz is not None and lz < LZ_THRESHOLD) or (gap is not None and gap > LEAK_Z_THRESHOLD))

    if flagged:
        rec = ("Результат требует подтверждения: профиль ответов нетипичен. Пройдите короткую "
               "подтверждающую форму с новыми заданиями — она доступна сразу.")
        status = "needs_confirmation"
        passed = False
        upgrade = False
    elif passed and upgrade:
        rec = (f"Уверенный результат: грейд {GRADE_NAMES[target_grade]} подтверждён, и вы можете сразу "
               f"пройти тест на {GRADE_NAMES[next_grade]} без ожидания периода смены грейда.")
        status = "passed_upgrade"
    elif passed:
        rec = f"Грейд {GRADE_NAMES[target_grade]} подтверждён."
        status = "passed"
    else:
        rec = (f"Уровень {GRADE_NAMES[target_grade]} пока не подтверждён. "
               + (f"Вы можете сразу пройти тест на {GRADE_NAMES[lower_grade]} — профиль не блокируется."
                  if lower_grade else "Повторная попытка будет доступна после периода ожидания."))
        status = "not_passed"
    return Outcome(
        theta=round(post.theta, 3),
        theta_se=round(post.se, 3),
        scaled_score=scaled_score(post.theta),
        raw_percent=round(raw, 1),
        passed=passed,
        upgrade_eligible=upgrade,
        outcome=status,
        confidence=round(p_target if passed or flagged else 1 - p_target, 3),
        verified_grade=target_grade if passed else None,
        competency_scores=competency_scores,
        recommendation=rec,
        posterior=post,
        flagged=flagged,
        person_fit=round(lz, 3) if lz is not None else None,
        leak_z=round(gap, 3) if gap is not None else None,
    )
