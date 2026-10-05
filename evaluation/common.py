"""Shared helpers for the offline evaluation scripts (no database, no server needed)."""

import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

RESULTS = Path(__file__).parent / "results"
DATA = Path(__file__).parent / "data"
RESULTS.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def stdev(xs):
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pearson(xs, ys):
    mx, my = mean(xs), mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / (sx * sy) if sx and sy else float("nan")


def cohen_kappa(a, b, labels, weighted=False):
    n = len(a)
    idx = {lab: i for i, lab in enumerate(labels)}
    k = len(labels)
    obs = [[0] * k for _ in range(k)]
    for x, y in zip(a, b, strict=True):
        obs[idx[x]][idx[y]] += 1
    ra = [sum(obs[i]) for i in range(k)]
    cb = [sum(obs[i][j] for i in range(k)) for j in range(k)]

    def w(i, j):
        return ((i - j) ** 2) / ((k - 1) ** 2) if weighted else (0 if i == j else 1)

    po = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(w(i, j) * ra[i] * cb[j] for i in range(k) for j in range(k)) / (n * n)
    return 1 - po / pe if pe else float("nan")


def auc(pos, neg):
    """Probability that a random positive scores above a random negative (Mann–Whitney)."""
    wins = 0.0
    for p in pos:
        for q in neg:
            wins += 1 if p > q else 0.5 if p == q else 0
    return wins / (len(pos) * len(neg))


def save(name: str, payload: dict, md: str) -> None:
    (RESULTS / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / f"{name}.md").write_text(md, encoding="utf-8")


def table(headers: list[str], rows: list[list]) -> str:
    def fmt(v):
        if isinstance(v, float):
            return f"{v:.3f}"
        return str(v)

    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(fmt(v) for v in r) + " |" for r in rows]
    return "\n".join(out)
