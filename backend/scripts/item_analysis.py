"""Item analysis on real attempts: how well every question separates weak and strong candidates.

    python scripts/item_analysis.py [--min-responses 30] [--spec backend] [--out report.md]

The same statistics the offline validation computes on synthetic candidates, but on the answers stored
in the database, so the procedure carries over to a pilot unchanged:

  * p    — share of correct answers (item easiness for the people who got it);
  * r_pb — item–rest point-biserial correlation (answer vs score on the rest of the form);
  * D    — upper–lower index: share correct in the top 27% minus the bottom 27% by rest score;
  * a verdict: D ≥ 0.3 good, 0.2–0.3 fair, < 0.2 — review (rewrite, recalibrate or retire the item).

Forms are targeted by grade, so every item is answered by a narrower ability range than the whole
population; r_pb and D are therefore lower bounds (restriction of range) — read them per grade band.
"""

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import AttemptStatus, Question, TestAttempt, TestItem  # noqa: E402


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / (sx * sy) if sx and sy else None


def analyse(responses: list[tuple[float, bool]]) -> dict:
    """responses: (rest score, correct) for every administration of one item."""
    rest = [r for r, _ in responses]
    u = [1.0 if c else 0.0 for _, c in responses]
    ranked = sorted(responses, key=lambda x: x[0])
    k = max(1, round(0.27 * len(ranked)))
    d = sum(c for _, c in ranked[-k:]) / k - sum(c for _, c in ranked[:k]) / k
    r = pearson(rest, u)
    verdict = "good" if d >= 0.3 else "fair" if d >= 0.2 else "review"
    return {"n": len(responses), "p": round(sum(u) / len(u), 3), "r_pb": round(r, 3) if r is not None else None,
            "d": round(d, 3), "verdict": verdict}


def collect(db, spec: str | None) -> dict[int, list[tuple[float, bool]]]:
    q = select(TestAttempt).where(TestAttempt.status != AttemptStatus.IN_PROGRESS).options(
        selectinload(TestAttempt.items).selectinload(TestItem.answer))
    if spec:
        q = q.where(TestAttempt.specialization_id == spec)
    by_item: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    for att in db.scalars(q):
        correct = {it.id: bool(it.answer and it.answer.is_correct) for it in att.items}
        total = sum(correct.values())
        for it in att.items:
            by_item[it.question_id].append((total - correct[it.id], correct[it.id]))
    return by_item


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-responses", type=int, default=30)
    ap.add_argument("--spec", default=None)
    ap.add_argument("--out", default=None, help="write the markdown report to a file")
    args = ap.parse_args()
    with SessionLocal() as db:
        by_item = collect(db, args.spec)
        questions = {q.id: q for q in db.scalars(select(Question).where(Question.id.in_(list(by_item))))}
    rows = []
    for qid, resp in by_item.items():
        if len(resp) < args.min_responses:
            continue
        q = questions[qid]
        rows.append({"code": q.code, "spec": q.specialization_id, "competency": q.competency_id,
                     "difficulty": q.difficulty, "family": bool(q.family), **analyse(resp)})
    rows.sort(key=lambda r: r["d"])
    lines = [f"# Анализ заданий: {len(rows)} заданий с ≥ {args.min_responses} ответами "
             f"(всего администрировано {len(by_item)})", ""]
    if rows:
        share = {v: sum(1 for r in rows if r["verdict"] == v) / len(rows) for v in ("good", "fair", "review")}
        lines += [f"D ≥ 0,3: {share['good']:.0%} · 0,2–0,3: {share['fair']:.0%} · на пересмотр: {share['review']:.0%}",
                  "", "| Код | Спец. | Компетенция | Сложн. | Параметрич. | n | p | r_pb | D | Вердикт |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        lines += [f"| {r['code']} | {r['spec']} | {r['competency']} | {r['difficulty']} | {'да' if r['family'] else ''} | "
                  f"{r['n']} | {r['p']} | {r['r_pb']} | {r['d']} | {r['verdict']} |" for r in rows]
    else:
        lines.append("Недостаточно ответов — снизьте --min-responses или дождитесь пилота.")
    md = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    sys.stdout.buffer.write(md.encode("utf-8"))


if __name__ == "__main__":
    main()
