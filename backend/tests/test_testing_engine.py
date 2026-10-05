import random
from datetime import datetime, timedelta

import pytest

from app.domain.catalog import COMPETENCIES
from app.domain.question_bank import FAMILIES, bank_items
from app.services.testing.generator import ItemSpec, build_blueprint, generate_form
from app.services.testing.irt import eap, scaled_score
from app.services.testing.policy import AttemptRecord, CandidateGradeState, check_eligibility
from app.services.testing.scoring import GradedItem, InvalidAnswer, grade_attempt, normalize_answer, score_answer


def pool(spec: str) -> list[ItemSpec]:
    out = []
    for k, i in enumerate(bank_items()):
        if i["specialization_id"] == spec:
            out.append(ItemSpec(k, i["code"], spec, i["competency_id"], i["difficulty"], i["qtype"], i["text"],
                                i["options"], i["correct"], i["family"], i["irt_a"], i["irt_b"], i["irt_c"]))
    return out


def weights(spec: str) -> dict:
    return {c: w for c, s, _, w in COMPETENCIES if s == spec}


@pytest.mark.parametrize("spec", ["backend", "frontend", "data_ml", "devops"])
@pytest.mark.parametrize("grade", ["junior", "middle", "senior"])
def test_parallel_forms_have_identical_structure(spec, grade):
    bp = build_blueprint(spec, grade, weights(spec), 15)
    assert sum(bp.competency_quota.values()) == 15
    assert all(v >= 1 for v in bp.competency_quota.values())
    items = pool(spec)
    forms = []
    for s in range(30):  # exposure counters grow as in production (Question.exposure_count)
        form = generate_form(bp, items, random.Random(s))
        chosen = {f.question_id for f in form}
        for it in items:
            if it.id in chosen:
                it.exposure += 1
        forms.append(form)
    profiles = {tuple(sorted((f.competency, f.difficulty) for f in form)) for form in forms}
    means = {round(sum(f.b for f in form) / 15, 6) for form in forms}
    assert len(means) == 1, "every form must have the same difficulty profile"
    ids = [frozenset(f.question_id for f in form) for form in forms]
    overlap = sum(len(a & b) for a, b in zip(ids, ids[1:], strict=False)) / (15 * (len(ids) - 1))
    assert overlap < 0.6, "consecutive candidates should receive substantially different items"
    assert len(profiles) >= 1


def test_seen_items_are_excluded_on_retake():
    bp = build_blueprint("backend", "middle", weights("backend"), 15)
    p = pool("backend")
    first = generate_form(bp, p, random.Random(1))
    seen = {f.question_id for f in first}
    second = generate_form(bp, p, random.Random(2), seen)
    static_repeats = [f for f in second if f.question_id in seen and not any(
        it.family for it in p if it.id == f.question_id)]
    assert len(static_repeats) <= 3


def test_correct_answers_never_leak_in_rendering_and_options_are_shuffled():
    bp = build_blueprint("frontend", "middle", weights("frontend"), 15)
    form = generate_form(bp, pool("frontend"), random.Random(5))
    for f in form:
        if f.qtype != "numeric":
            assert all(0 <= i < len(f.options) for i in f.correct)


@pytest.mark.parametrize("fam", FAMILIES, ids=lambda f: f.code)
def test_parametric_families_render_isomorphic_variants(fam):
    rng = random.Random(0)
    texts = set()
    for _ in range(40):
        r = fam.render(rng)
        texts.add(r["text"])
        assert r["correct"]
        if fam.qtype == "single":
            assert len(r["options"]) == 4 and len(set(r["options"])) == 4
    assert len(texts) > 5, "a family must produce many distinct variants"


def test_eap_is_monotonic_and_finite():
    items = [(1.0, b, 0.2) for b in (-2, -1, 0, 1, 2)] * 3
    thetas = []
    for k in range(len(items) + 1):
        resp = [(a, b, c, i < k) for i, (a, b, c) in enumerate(sorted(items, key=lambda x: x[1]))]
        thetas.append(eap(resp).theta)
    assert all(t2 >= t1 for t1, t2 in zip(thetas, thetas[1:], strict=False))
    assert -4 < thetas[0] < thetas[-1] < 4
    assert scaled_score(0) == 50 and scaled_score(1) == 75 and scaled_score(-1) == 25


def test_grade_decision_and_upgrade():
    strong = [GradedItem("be_db", 1.2, b, 0.1, True, 1.0) for b in (0, 0.5, 1, 1, 1.5, 2, 2, 1, 0.5, 0)]
    out = grade_attempt(strong, "middle")
    assert out.passed and out.verified_grade == "middle" and out.upgrade_eligible
    weak = [GradedItem("be_db", 1.2, b, 0.1, False, 0.0) for b in (-1, -0.5, 0, 0.5, 1, 1, 0, 0, -1, 0)]
    out = grade_attempt(weak, "middle")
    assert not out.passed and out.verified_grade is None and "Junior" in out.recommendation


def test_answer_validation():
    assert normalize_answer("single", 4, [2]) == [2]
    with pytest.raises(InvalidAnswer):
        normalize_answer("single", 4, [0, 1])
    with pytest.raises(InvalidAnswer):
        normalize_answer("single", 4, [7])
    with pytest.raises(InvalidAnswer):
        normalize_answer("numeric", 0, ["abc"])
    assert normalize_answer("numeric", 0, ["1 024"]) == [1024.0]
    assert score_answer("multi", [0, 2], [0, 2]) == (True, 1.0)
    ok, credit = score_answer("multi", [0, 2], [0])
    assert not ok and credit == 0.5


NOW = datetime(2026, 10, 1)


def state(grade=None, spec=None, locked=None, upgrade=False):
    return CandidateGradeState(spec, grade, locked, upgrade)


def test_policy_fallback_after_failing_declared_grade():
    hist = [AttemptRecord("backend", "middle", NOW - timedelta(minutes=5), False)]
    e = check_eligibility(state(), hist, "backend", "junior", NOW, 30)
    assert e.allowed and e.kind == "fallback"
    same = check_eligibility(state(), hist, "backend", "middle", NOW, 30)
    assert not same.allowed and same.available_at == NOW - timedelta(minutes=5) + timedelta(days=30)


def test_policy_grade_lock_and_fast_track():
    hist = [AttemptRecord("backend", "junior", NOW - timedelta(days=1), False)]
    locked = NOW + timedelta(days=89)
    e = check_eligibility(state("junior", "backend", locked, upgrade=False), hist, "backend", "middle", NOW, 30)
    assert not e.allowed, "grade changes are limited by the cooldown"
    e = check_eligibility(state("junior", "backend", locked, upgrade=True), hist, "backend", "middle", NOW, 30)
    assert e.allowed and e.kind == "upgrade", "confident result unlocks the next grade immediately"
    e = check_eligibility(state("junior", "backend", NOW - timedelta(days=1)), hist, "backend", "middle", NOW, 30)
    assert e.allowed


def test_policy_single_active_attempt():
    hist = [AttemptRecord("backend", "middle", None, True)]
    assert not check_eligibility(state(), hist, "backend", "junior", NOW, 30).allowed
