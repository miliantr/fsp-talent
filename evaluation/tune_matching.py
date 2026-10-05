"""Hyper-parameter tuning of the Matching Engine on the synthetic benchmark.

    python evaluation/tune_matching.py

Grid search on a TRAIN world (seed 11), the best configuration is then checked on an independent
held-out world (seed 23) to make sure we are not overfitting the synthetic labels.
Tuned: must-have gate floor, strength of test evidence for declared skills, share of competency
scores inside the test component, and the weight preset (component weights).
"""

import itertools
import random
import time

from common import mean, save, table
from evaluate_matching import make_candidate, make_job, metrics, rank_engine, relevance

from app.repositories.reference import skill_graph
from app.services.matching import config as mcfg
from app.services.matching import engine

GRID = {
    "MUST_GATE_FLOOR": [0.5, 0.65, 0.8, 1.0],
    "EVIDENCE_STRENGTH": [0.0, 0.25, 0.5],
    "TEST_COMPETENCY_SHARE": [0.0, 0.35],
}
# The first expert configuration of the engine (v1.0, before tuning) — the reference point.
INITIAL_CONFIG = {"MUST_GATE_FLOOR": 0.5, "EVIDENCE_STRENGTH": 0.5, "TEST_COMPETENCY_SHARE": 0.35}
INITIAL_WEIGHTS = {"skills": 0.28, "test": 0.20, "grade": 0.16, "specialization": 0.10, "fsp": 0.10,
                   "freshness": 0.06, "salary": 0.05, "experience": 0.03, "format": 0.02}

WEIGHT_VARIANTS = {
    "initial": INITIAL_WEIGHTS,
    "grade_heavier": {**INITIAL_WEIGHTS, "grade": 0.22, "test": 0.16, "skills": 0.26},
    "skills_heavier": {**INITIAL_WEIGHTS, "skills": 0.34, "test": 0.16, "grade": 0.16},
}


def world(seed: int, n_jobs=60, n_cands=600):
    rng = random.Random(seed)
    cands = [make_candidate(i, rng) for i in range(n_cands)]
    jobs = [make_job(j, rng) for j in range(n_jobs)]
    return jobs, cands


def score(jobs, cands, graph, labels_cache) -> float:
    res = []
    for job in jobs:
        labels = labels_cache[job["id"]]
        if not any(v >= 2 for v in labels.values()):
            continue
        res.append(metrics(rank_engine(job, cands, graph), labels))
    return {m: mean(r[m] for r in res) for m in res[0]}


def apply(cfg: dict, weights: dict):
    for k, v in cfg.items():
        setattr(engine, k, v)
    mcfg.PRESETS["balanced"] = weights


def main():
    graph = skill_graph()
    t0 = time.time()
    train = world(11)
    test = world(23)
    cache_tr = {j["id"]: {c["id"]: relevance(j, c, graph) for c in train[1]} for j in train[0]}
    cache_te = {j["id"]: {c["id"]: relevance(j, c, graph) for c in test[1]} for j in test[0]}
    production = ({k: getattr(engine, k) for k in GRID}, dict(mcfg.PRESETS["balanced"]))
    initial = (INITIAL_CONFIG, INITIAL_WEIGHTS)

    rows = []
    for values in itertools.product(*GRID.values()):
        cfg = dict(zip(GRID, values, strict=True))
        for wname, w in WEIGHT_VARIANTS.items():
            apply(cfg, w)
            m = score(*train, graph, cache_tr)
            rows.append((m["NDCG@10"], cfg, wname, m))
    rows.sort(key=lambda r: -r[0])
    best_ndcg, best_cfg, best_w, best_m = rows[0]

    apply(*initial)
    default_tr = score(*train, graph, cache_tr)
    default_te = score(*test, graph, cache_te)
    apply(best_cfg, WEIGHT_VARIANTS[best_w])
    best_te = score(*test, graph, cache_te)
    apply(*production)
    prod_tr = score(*train, graph, cache_tr)
    prod_te = score(*test, graph, cache_te)

    top = [[f"{r[1]}", r[2], round(r[0], 3), round(r[3]["P@10"], 3), round(r[3]["MRR"], 3)] for r in rows[:8]]
    md = "\n".join([
        "# Подбор гиперпараметров механики подбора",
        "",
        "Сетка на обучающем синтетическом мире (seed 11), проверка лучшей конфигурации на независимом "
        "мире (seed 23).",
        "",
        table(["Конфигурация", "Веса", "NDCG@10 (train)", "P@10", "MRR"], top),
        "",
        table(["", "NDCG@10 train", "NDCG@10 held-out", "P@10 held-out", "MRR held-out"], [
            ["Исходная экспертная конфигурация (v1.0)", round(default_tr["NDCG@10"], 3),
             round(default_te["NDCG@10"], 3), round(default_te["P@10"], 3), round(default_te["MRR"], 3)],
            ["Лучшая на сетке", round(best_ndcg, 3), round(best_te["NDCG@10"], 3), round(best_te["P@10"], 3),
             round(best_te["MRR"], 3)],
            ["Принятая в продукт (v1.2)", round(prod_tr["NDCG@10"], 3), round(prod_te["NDCG@10"], 3),
             round(prod_te["P@10"], 3), round(prod_te["MRR"], 3)],
        ]),
        "",
        f"Продуктовая конфигурация: `{production[0]}`, веса balanced = `{production[1]}`. "
        "EVIDENCE_STRENGTH оставлен 0,25 (а не 0 как на сетке): подтверждённые тестом навыки — продуктовый "
        "стимул проходить тест; потеря NDCG в пределах ~0,01.",
        "",
        f"Лучшее: `{best_cfg}`, веса `{best_w}`. Время: {time.time() - t0:.0f} с.",
        "",
    ])
    save("tuning_report", {"best": {"config": best_cfg, "weights": best_w}, "train_initial": default_tr,
                           "heldout_initial": default_te, "heldout_best": best_te, "train_production": prod_tr,
                           "heldout_production": prod_te,
                           "top": [{"config": r[1], "weights": r[2], "ndcg": r[0]} for r in rows[:20]]}, md)
    print(md)


if __name__ == "__main__":
    main()
