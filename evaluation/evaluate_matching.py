"""Offline benchmark of the Matching Engine.

    python evaluation/evaluate_matching.py [--jobs 60] [--candidates 600] [--seed 11]
    python evaluation/evaluate_matching.py --dataset path/to/benchmark.json   # your own labelled pairs

Ground truth. Every synthetic candidate has a LATENT profile: true specialization, true ability θ,
true skill set. The engine never sees it. It sees only what the platform observes:
  * a self-declared CV: true skills with omissions, plus "padded" skills the person does not have
    (40% of candidates), noisy self-assessed levels;
  * the verified category and competency scores produced by the test (noisy measurements of θ and
    of the true skills);
  * FSP achievements (more likely and stronger for strong people, absent for ~50%);
  * salary expectation, format, activity date.
Relevance labels 0..3 for each (job, candidate) pair are assigned by explicit expert rules over the
LATENT profile (true specialization fit, true grade fit, true must-have coverage, salary
compatibility). The rules do not use the engine's weights.

Metrics: Precision@K, Recall@K, MRR (first pair with label ≥ 2), NDCG@K (graded labels).
Baselines: random; keyword search over the CV (the "classic job board"); keyword + declared grade.
Ablations: the engine without test evidence / skill graph / FSP / must-have gate; weight presets.
"""

import argparse
import json
import math
import random
import time
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta

from common import DATA, mean, save, table

from app.domain.catalog import GRADE_CUTS, GRADE_RANK, SKILLS, spec_similarity
from app.repositories.reference import skill_graph
from app.seed.personas import EXTRAS, STACKS
from app.services.fsp.scoring import AchievementLike, summarize
from app.services.matching import engine
from app.services.matching.config import PRESETS
from app.services.matching.engine import CandidateFeatures, JobFeatures, SkillGraph, SkillInfo

NOW = datetime(2026, 10, 1)
SPECS = ["backend", "frontend", "data_ml", "devops"]
GRADES = ["junior", "middle", "senior"]
THETA_BAND = {"junior": (-1.0, 0.0), "middle": (0.0, 1.0), "senior": (1.0, 2.3)}
SALARY = {"junior": (70_000, 130_000), "middle": (150_000, 270_000), "senior": (280_000, 460_000)}
ALL_SKILLS = [s[0] for s in SKILLS]
COMP_OF = {s[0]: s[4] for s in SKILLS}
K = 10


def grade_of(theta: float) -> str:
    return "senior" if theta >= 1 else "middle" if theta >= 0 else "junior"


# ------------------------------------------------------------------ synthetic world

def make_candidate(i: int, rng: random.Random) -> dict:
    spec = rng.choice(SPECS)
    grade = rng.choices(GRADES, weights=[0.35, 0.4, 0.25])[0]
    theta = rng.uniform(*THETA_BAND[grade])
    stack = list(rng.choice(STACKS[spec]))
    true_skills = {s: min(5, max(1, round(2 + 1.2 * theta + rng.gauss(0, 0.7)))) for s in stack}
    declared = {s: lvl for s, lvl in true_skills.items() if rng.random() > 0.1}  # omissions
    if rng.random() < 0.4:
        # keyword stuffing: trendy skills of the SAME field the person does not really have
        field = sorted({t for st in STACKS[spec] for t in st} | set(EXTRAS[spec]) - set(true_skills))
        for s in rng.sample(field, min(3, len(field))):
            declared.setdefault(s, rng.randint(3, 5))
    declared = {s: min(5, max(1, lvl + rng.choice([-1, 0, 0, 1, 1]))) for s, lvl in declared.items()}

    # what the test observes: θ with the measurement error of a 20-item form (SE ≈ 0.33)
    theta_hat = theta + rng.gauss(0, 0.33)
    comps = {}
    for comp_map in COMP_OF.values():
        comp = comp_map.get(spec)
        if not comp or comp in comps:
            continue
        knows = any(COMP_OF.get(t, {}).get(spec) == comp for t in true_skills)
        offset = 0.5 if knows else -0.6
        p = 1 / (1 + math.exp(-1.7 * (theta + offset - 0.3)))
        comps[comp] = max(0, min(100, round(100 * p + rng.gauss(0, 12))))
    verified = grade_of(theta_hat)

    fsp = None
    if rng.random() < 0.5:
        n = rng.randint(1, 4)
        achs = []
        for _ in range(n):
            strong = rng.random() < 0.15 + 0.25 * (theta + 1) / 3.3
            achs.append(AchievementLike("Соревнования ФСП", "Продуктовое программирование",
                                        rng.choice(["regional", "interregional", "all_russian"]),
                                        date(2026, 1, 1) - timedelta(days=rng.randint(30, 1000)),
                                        rng.randint(1, 3) if strong else rng.choice([None, rng.randint(10, 60)]),
                                        100, None, spec))
        fsp = achs
    return {
        "id": i, "spec": spec, "theta": theta, "true_grade": grade, "true_skills": true_skills,
        "declared_skills": declared, "declared_grade": declared_grade(grade, rng),
        "verified_grade": verified, "theta_hat": theta_hat,
        "competency_scores": comps, "fsp": fsp,
        "expected_salary": round(rng.uniform(*SALARY[grade]) * rng.uniform(0.9, 1.25), -4),
        "work_format": rng.choice(["remote", "hybrid", "office", "any"]),
        "days_ago": rng.choice([3, 10, 30, 60, 120, 250]),
    }


def declared_grade(grade: str, rng: random.Random) -> str:
    """Self-assessment: over-claiming by one level is common (30%), under-claiming rarer (10%)."""
    i = GRADES.index(grade)
    r = rng.random()
    if r < 0.3:
        i = min(2, i + 1)
    elif r < 0.4:
        i = max(0, i - 1)
    return GRADES[i]


def make_job(j: int, rng: random.Random) -> dict:
    spec = rng.choice(SPECS)
    grade = rng.choices(GRADES, weights=[0.25, 0.45, 0.3])[0]
    stack = list(rng.choice(STACKS[spec]))
    must = rng.sample(stack, k=min(len(stack), rng.randint(2, 4)))
    nice = [s for s in stack if s not in must][:2]
    lo, hi = SALARY[grade]
    return {"id": j, "spec": spec, "grade": grade, "must": must, "nice": nice,
            "salary_from": lo, "salary_to": hi, "work_format": rng.choice(["remote", "hybrid", "any"])}


def relevance(job: dict, c: dict, graph: SkillGraph) -> int:
    """Expert rules over the LATENT profile: a utility of hiring this person for this need.
    3 = ideal, 2 = good, 1 = weak, 0 = irrelevant."""
    sim = spec_similarity(c["spec"], job["spec"])
    spec_fit = 1.0 if sim >= 1 else 0.4 if sim >= 0.3 else 0.0
    d = GRADE_RANK[c["true_grade"]] - GRADE_RANK[job["grade"]]
    grade_fit = {0: 1.0, 1: 0.75, -1: 0.45}.get(d, 0.0)
    cov = 0.0
    for s in job["must"]:
        best = max((graph.similarity(t, s) for t in c["true_skills"]), default=0)
        cov += 1.0 if best >= 1 else 0.5 if best >= 0.5 else 0.0
    cov /= len(job["must"])
    lo = THETA_BAND[c["true_grade"]][0]
    ability = 0.85 + 0.3 * min(1.0, c["theta"] - lo) if d == 0 else 1.0  # stronger within the band
    salary = 0.6 if c["expected_salary"] > job["salary_to"] * 1.3 else 1.0
    u = spec_fit * grade_fit * (0.25 + 0.75 * cov) * ability * salary
    return 3 if u >= 0.8 else 2 if u >= 0.6 else 1 if u >= 0.4 else 0


# ------------------------------------------------------------------ rankers

def features(c: dict, *, use_test=True, use_fsp=True, declared_grade=False) -> CandidateFeatures:
    fsp_by_spec = {}
    if use_fsp and c["fsp"]:
        fsp_by_spec = {s: summarize(c["fsp"], s, NOW.date()) for s in SPECS}
    return CandidateFeatures(
        id=c["id"], specialization=c["spec"], grade=c["declared_grade"] if declared_grade else c["verified_grade"],
        theta=c["theta_hat"] if use_test else GRADE_CUTS[c["declared_grade" if declared_grade else "verified_grade"]] + 0.5,
        scaled_score=round(50 + 25 * c["theta_hat"]), confidence=0.85,
        competency_scores=c["competency_scores"] if use_test else {},
        skills=c["declared_skills"], experience_years=2.0, expected_salary=c["expected_salary"],
        work_format=c["work_format"], last_active_at=NOW - timedelta(days=c["days_ago"]),
        verified_at=NOW - timedelta(days=c["days_ago"]), fsp_by_spec=fsp_by_spec,
    )


def job_features(j: dict, preset="balanced") -> JobFeatures:
    return JobFeatures(id=j["id"], specialization=j["spec"], grade=j["grade"], must_skills=j["must"],
                       nice_skills=j["nice"], salary_from=j["salary_from"], salary_to=j["salary_to"],
                       work_format=j["work_format"], weights_preset=preset)


def rank_engine(job, cands, graph, preset="balanced", use_test=True, use_fsp=True, gate=True, declared=False):
    feats = [features(c, use_test=use_test, use_fsp=use_fsp, declared_grade=declared) for c in cands]
    jf = job_features(job, preset)
    if not gate:
        saved = engine.MUST_GATE_FLOOR, engine.MUST_GATE_FULL
        engine.MUST_GATE_FLOOR, engine.MUST_GATE_FULL = 1.0, 1.0
    try:
        return [m.candidate_id for m in engine.rank(feats, jf, graph, NOW)]
    finally:
        if not gate:
            engine.MUST_GATE_FLOOR, engine.MUST_GATE_FULL = saved


def rank_keyword(job, cands, rng, use_grade=False):
    """Classic job-board search: keyword overlap with the self-declared CV."""
    scored = []
    for c in cands:
        s = sum(1 for k in job["must"] if k in c["declared_skills"]) + 0.5 * sum(
            1 for k in job["nice"] if k in c["declared_skills"])
        if use_grade and c["declared_grade"] == job["grade"]:
            s += 1
        if s > 0:
            scored.append((s, rng.random(), c["id"]))
    scored.sort(reverse=True)
    return [i for _, _, i in scored]


def rank_random(job, cands, rng):
    ids = [c["id"] for c in cands if c["spec"] == job["spec"]]
    rng.shuffle(ids)
    return ids


# ------------------------------------------------------------------ metrics

def metrics(ranked: list[int], labels: dict[int, int], k: int = K) -> dict:
    rel = {i for i, lbl in labels.items() if lbl >= 2}
    top = ranked[:k]
    hits = sum(1 for i in top if i in rel)
    p = hits / k
    r = hits / len(rel) if rel else 0.0
    rr = next((1 / (pos + 1) for pos, i in enumerate(ranked) if i in rel), 0.0)
    dcg = sum((2 ** labels.get(i, 0) - 1) / math.log2(pos + 2) for pos, i in enumerate(top))
    ideal = sorted(labels.values(), reverse=True)[:k]
    idcg = sum((2 ** g - 1) / math.log2(pos + 2) for pos, g in enumerate(ideal))
    p5 = sum(1 for i in ranked[:5] if i in rel) / 5
    return {"P@5": p5, f"P@{k}": p, f"R@{k}": r, "MRR": rr, f"NDCG@{k}": dcg / idcg if idcg else 0.0}


def evaluate(jobs, cands, graph, rankers) -> dict:
    out = {}
    for name, fn in rankers.items():
        rows = []
        for job in jobs:
            labels = {c["id"]: relevance(job, c, graph) for c in cands}
            if sum(1 for v in labels.values() if v >= 2) == 0:
                continue
            rows.append(metrics(fn(job), labels))
        out[name] = {m: round(mean(r[m] for r in rows), 3) for m in rows[0]}
        out[name]["jobs"] = len(rows)
    return out


def fsp_fairness(jobs, cands, graph) -> dict:
    """Do candidates WITHOUT FSP history get buried? Compare their average rank percentile with that
    of candidates WITH history at the same relevance label."""
    res = {"with_fsp": [], "without_fsp": []}
    for job in jobs:
        ranked = rank_engine(job, cands, graph)
        pos = {cid: k / max(1, len(ranked) - 1) for k, cid in enumerate(ranked)}
        for c in cands:
            if c["id"] in pos and relevance(job, c, graph) == 3:
                res["with_fsp" if c["fsp"] else "without_fsp"].append(pos[c["id"]])
    return {k: round(mean(v), 3) for k, v in res.items()} | {"n": {k: len(v) for k, v in res.items()}}


def run(n_jobs: int, n_cands: int, seed: int, dataset: str | None) -> dict:
    rng = random.Random(seed)
    graph = skill_graph()
    if dataset:
        data = json.loads(open(dataset, encoding="utf-8").read())
        jobs, cands = data["jobs"], data["candidates"]
    else:
        cands = [make_candidate(i, rng) for i in range(n_cands)]
        jobs = [make_job(j, rng) for j in range(n_jobs)]
        export = {"description": "Synthetic job↔candidate benchmark (labels from latent profiles)",
                  "seed": seed, "jobs": jobs,
                  "candidates": [{**c, "fsp": [asdict(a) | {"date": a.date.isoformat()} for a in c["fsp"]]
                                  if c["fsp"] else None} for c in cands]}
        (DATA / "matching_benchmark.json").write_text(json.dumps(export, ensure_ascii=False, indent=1),
                                                      encoding="utf-8")
    for c in cands:
        if c["fsp"] and isinstance(c["fsp"][0], dict):
            c["fsp"] = [AchievementLike(**{**a, "date": date.fromisoformat(a["date"])}) for a in c["fsp"]]

    no_graph = SkillGraph([replace(SkillInfo(s, n, cm, {}), related={}) for s, n, _k, _a, cm, _r in SKILLS])
    rr = random.Random(seed + 1)
    rankers = {
        "Random (same specialization)": lambda j: rank_random(j, cands, rr),
        "Keyword search over CV": lambda j: rank_keyword(j, cands, rr),
        "Keyword + declared grade": lambda j: rank_keyword(j, cands, rr, use_grade=True),
        "FSP Talent engine (balanced)": lambda j: rank_engine(j, cands, graph),
        "— no testing at all (self-declared grade)": lambda j: rank_engine(j, cands, graph, use_test=False,
                                                                          declared=True),
        "— verified grade only (no θ, no competencies)": lambda j: rank_engine(j, cands, graph, use_test=False),
        "— without skill graph": lambda j: rank_engine(j, cands, no_graph),
        "— without FSP signal": lambda j: rank_engine(j, cands, graph, use_fsp=False),
        "— without must-have gate": lambda j: rank_engine(j, cands, graph, gate=False),
    }
    for preset in PRESETS:
        if preset != "balanced":
            rankers[f"Preset: {preset}"] = (lambda p: (lambda j: rank_engine(j, cands, graph, preset=p)))(preset)
    res = evaluate(jobs, cands, graph, rankers)
    return {"seed": seed, "jobs": len(jobs), "candidates": len(cands), "k": K, "results": res,
            "fsp_fairness": fsp_fairness(jobs, cands, graph),
            "label_distribution": {
                str(v): sum(1 for j in jobs for c in cands if relevance(j, c, graph) == v) for v in range(4)}}


def markdown(r: dict) -> str:
    names = list(r["results"])
    cols = [m for m in r["results"][names[0]] if m != "jobs"]
    fair = r["fsp_fairness"]
    return "\n".join([
        "# Валидация механики подбора",
        "",
        f"Синтетический бенчмарк: {r['jobs']} потребностей × {r['candidates']} кандидатов (seed={r['seed']}). "
        "Метки релевантности 0–3 назначены экспертными правилами по скрытому «истинному» профилю "
        "(специализация, истинный грейд, реальное покрытие must-have навыков, зарплата). Ранжировщики видят "
        "только наблюдаемые данные: резюме с пропусками и «приписанными» навыками, результаты теста, ФСП.",
        "",
        "Релевантным считается кандидат с меткой ≥ 2.",
        "",
        table(["Ранжировщик"] + cols, [[n] + [r["results"][n][c] for c in cols] for n in names]),
        "",
        "## Кандидаты без истории ФСП не «топятся»",
        "Средний перцентиль позиции идеальных (метка 3) кандидатов в выдаче (0 — первое место):",
        "",
        table(["Группа", "Средний перцентиль", "N"],
              [["С достижениями ФСП", fair["with_fsp"], fair["n"]["with_fsp"]],
               ["Без истории ФСП", fair["without_fsp"], fair["n"]["without_fsp"]]]),
        "",
        "Распределение меток: " + ", ".join(f"{k}: {v}" for k, v in r["label_distribution"].items()),
        "",
    ])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=60)
    ap.add_argument("--candidates", type=int, default=600)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--dataset", help="JSON with {jobs, candidates} in the exported format")
    args = ap.parse_args()
    t0 = time.time()
    rep = run(args.jobs, args.candidates, args.seed, args.dataset)
    rep["runtime_sec"] = round(time.time() - t0, 1)
    md = markdown(rep)
    save("matching_report", rep, md)
    print(md)
    print(f"Saved to evaluation/results/matching_report.(json|md) in {rep['runtime_sec']} s")
