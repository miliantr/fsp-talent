from datetime import date, datetime, timedelta

from app.repositories.reference import skill_graph
from app.services.fsp.scoring import AchievementLike, summarize
from app.services.matching.engine import CandidateFeatures, JobFeatures, compare, is_eligible, rank, score_candidate

NOW = datetime(2026, 10, 1)
GRAPH = skill_graph()


def cand(cid=1, spec="backend", grade="middle", theta=0.6, skills=None, comp=None, fsp=None, salary=None, **kw):
    return CandidateFeatures(
        id=cid, specialization=spec, grade=grade, theta=theta, scaled_score=round(50 + 25 * theta),
        confidence=0.9, competency_scores=comp if comp is not None else {"be_lang": 80, "be_db": 75, "be_api": 70,
                                                                         "be_ops": 70},
        skills=skills if skills is not None else {"python": 4, "fastapi": 4, "postgresql": 4, "docker": 3},
        expected_salary=salary, last_active_at=NOW - timedelta(days=5), verified_at=NOW - timedelta(days=5),
        fsp_by_spec={"backend": fsp} if fsp else {}, **kw)


JOB = JobFeatures(id=1, specialization="backend", grade="middle",
                  must_skills=["python", "fastapi", "postgresql", "docker"], nice_skills=["redis"],
                  salary_from=180_000, salary_to=250_000)


def fsp_summary(place=1):
    a = AchievementLike("Всероссийские соревнования", "Продуктовое программирование", "all_russian",
                        date(2026, 3, 1), place, 100, "backend", "backend")
    return summarize([a], "backend", date(2026, 10, 1))


def test_no_fsp_history_is_neutral_not_zero():
    without = score_candidate(cand(), JOB, GRAPH, NOW)
    weak_fsp = score_candidate(cand(fsp=fsp_summary(place=None)), JOB, GRAPH, NOW)
    strong_fsp = score_candidate(cand(fsp=fsp_summary(place=1)), JOB, GRAPH, NOW)
    assert without.components["fsp"].value > 0
    assert without.percent >= 60, "a good candidate without FSP history must still rank high"
    assert strong_fsp.score > weak_fsp.score >= without.score, "any participation can only help"
    assert any("Нет истории ФСП" in r.text for r in without.reasons)


def test_skill_graph_gives_partial_credit_and_evidence_matters():
    exact = score_candidate(cand(), JOB, GRAPH, NOW)
    related = score_candidate(cand(skills={"python": 4, "flask": 4, "mysql": 4, "docker": 3}), JOB, GRAPH, NOW)
    missing = score_candidate(cand(skills={"java": 4, "spring": 4}), JOB, GRAPH, NOW)
    assert exact.score > related.score > missing.score
    assert {m.status for m in related.skill_matches if m.importance == "must"} >= {"exact", "related"}
    unverified = score_candidate(cand(comp={}), JOB, GRAPH, NOW)
    assert exact.components["skills"].value > unverified.components["skills"].value, \
        "skills confirmed by test competencies weigh more than self-declared ones"


def test_grade_and_spec_gates():
    assert not is_eligible(cand(grade="junior"), JobFeatures(2, "backend", "senior", ["python"]))
    assert is_eligible(cand(spec="devops"), JOB), "adjacent specialization stays visible with partial score"
    assert score_candidate(cand(spec="devops"), JOB, GRAPH, NOW).score < score_candidate(cand(), JOB, GRAPH, NOW).score


def test_missing_salary_is_unavailable_not_penalised():
    m = score_candidate(cand(salary=None), JOB, GRAPH, NOW)
    assert not m.components["salary"].available and m.components["salary"].weight == 0
    over = score_candidate(cand(salary=400_000), JOB, GRAPH, NOW)
    inside = score_candidate(cand(salary=200_000), JOB, GRAPH, NOW)
    assert inside.score > over.score


def test_ranking_and_explanations():
    pool = [cand(1), cand(2, theta=1.2, fsp=fsp_summary()), cand(3, skills={"go": 4}), cand(4, grade="senior",
                                                                                          theta=1.8)]
    ranked = rank(pool, JOB, GRAPH, NOW)
    assert ranked[0].candidate_id == 2
    assert ranked[-1].candidate_id == 3
    for m in ranked:
        assert m.reasons and abs(sum(c.contribution for c in m.components.values()) - m.score * 100) < 0.5
    diff = compare(ranked[0], ranked[-1])
    assert diff["delta_percent"] > 0 and diff["summary"]
