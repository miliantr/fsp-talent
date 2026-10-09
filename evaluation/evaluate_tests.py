"""Validation of the Testing Engine on synthetic candidates.

    python evaluation/evaluate_tests.py [--n 400] [--seed 7]

There is no reference dataset in the hackathon, so validity is checked by simulation with a
known ground truth (a standard psychometric approach):

  * every synthetic candidate has a TRUE ability θ and therefore a true grade
    (θ < −1 → below Junior, [−1,0) Junior, [0,1) Middle, ≥1 Senior);
  * answers are simulated with the 3PL model using *perturbed* "true" item parameters
    (b + N(0, 0.35), a · LogNormal(0, 0.2)) — the engine scores with its NOMINAL parameters,
    so the evaluation includes model misspecification instead of being circular;
  * the production code is used end-to-end: blueprint → form generation → scoring → grade rules.

Metrics:
  1. Grade classification vs ground truth (accuracy, weighted κ, over-/under-grading).
  2. Test–retest: (a) the same profile goes through the whole grading procedure twice on fresh
     forms — agreement of the ASSIGNED grades; (b) two parallel forms of one target grade.
  3. Form equivalence: spread of form difficulty for blueprint forms vs naive random forms.
  4. Discrimination: item–rest point-biserial, upper–lower index D per item, AUC, score by grade.
  5. Leak resistance: pass-rate inflation for a weak candidate who memorised K leaked forms,
     compared with a single fixed test.
  6. Item calibration: recovery of the true difficulties from response data.
  8. Behavioural integrity (cheating detection): detection and false-positive rates for simulated
     honest candidates, «look it up elsewhere» cheaters and pre-knowledge cheaters, with a
     response-time model.
  9. Speed of generating, scoring and checking a test.
"""

import argparse
import math
import random
import time

from common import auc, cohen_kappa, mean, pearson, save, stdev, table

from app.core.config import get_settings
from app.domain.catalog import COMPETENCIES, GRADE_CUTS
from app.domain.question_bank import bank_items
from app.services.testing.generator import DIFFICULTY_PROFILE, ItemSpec, build_blueprint, generate_form
from app.services.testing.integrity import ClientEvents, ItemTrace, assess, expected_seconds
from app.services.testing.irt import p_correct, scaled_score
from app.services.testing.scoring import GradedItem, grade_attempt

SPECS = ["backend", "frontend", "data_ml", "devops"]
GRADES = ["junior", "middle", "senior"]
LOWER = {"senior": "middle", "middle": "junior", "junior": None}
LEN = get_settings().test_length


def true_grade(theta: float) -> str:
    if theta >= GRADE_CUTS["senior"]:
        return "senior"
    if theta >= GRADE_CUTS["middle"]:
        return "middle"
    if theta >= GRADE_CUTS["junior"]:
        return "junior"
    return "none"


class Bank:
    def __init__(self, spec: str, rng: random.Random):
        self.items: list[ItemSpec] = []
        self.true: dict[int, tuple[float, float, float]] = {}
        for k, i in enumerate(bank_items()):
            if i["specialization_id"] != spec:
                continue
            it = ItemSpec(k, i["code"], spec, i["competency_id"], i["difficulty"], i["qtype"], i["text"],
                          i["options"], i["correct"], i["family"], i["irt_a"], i["irt_b"], i["irt_c"])
            self.items.append(it)
            self.true[k] = (it.a * math.exp(rng.gauss(0, 0.2)), it.b + rng.gauss(0, 0.35), it.c)
        self.weights = {c: w for c, s, _, w in COMPETENCIES if s == spec}
        self.blueprints = {g: build_blueprint(spec, g, self.weights, LEN) for g in GRADES}

    def form(self, grade: str, rng: random.Random, seen=None, exposure=True):
        f = generate_form(self.blueprints[grade], self.items, rng, seen)
        if exposure:
            ids = {x.question_id for x in f}
            for it in self.items:
                if it.id in ids:
                    it.exposure += 1
        return f


def answer(form, theta, bank: Bank, rng, known: set[int] | None = None):
    out = []
    for it in form:
        a, b, c = bank.true[it.question_id]
        if known and it.question_id in known and not it.family:
            ok = True  # leaked static item: the answer is memorised
        else:
            ok = rng.random() < p_correct(theta, a, b, c)
        out.append(GradedItem(it.competency, it.a, it.b, it.c, ok, 1.0 if ok else 0.0, it.family is not None))
    return out


def take(bank, grade, theta, rng, seen=None, known=None, length=None):
    if length:
        form = generate_form(build_blueprint(bank.items[0].specialization, grade, bank.weights, length),
                             bank.items, rng, seen)
    else:
        form = bank.form(grade, rng, seen)
    graded = answer(form, theta, bank, rng, known)
    return form, graded, grade_attempt(graded, grade)


def take_with_confirmation(bank, grade, theta, rng, seen=None, known=None):
    """A flagged result is re-checked by one fresh confirmation form (production policy)."""
    form, graded, out = take(bank, grade, theta, rng, seen, known)
    seen = (seen or set()) | {f.question_id for f in form}
    flagged = out.flagged
    if flagged:
        form, graded, out = take(bank, grade, theta, rng, seen, known)
        seen |= {f.question_id for f in form}
    return out, seen, flagged


def protocol(bank, declared, theta, rng, seen=None):
    """Production rules: test on the declared grade; on failure — optional lower-grade test.
    Items the candidate has already seen are excluded, as in production."""
    out, seen, flag = take_with_confirmation(bank, declared, theta, rng, seen)
    tests, flags = 1 + flag, int(flag)
    grade = declared
    while not out.passed and LOWER[grade]:
        grade = LOWER[grade]
        out, seen2, flag = take_with_confirmation(bank, grade, theta, rng, seen)
        seen |= seen2
        tests += 1 + flag
        flags += int(flag)
    return (out.verified_grade or "none"), out, tests, flags, seen


def nearest_cut_distance(theta: float) -> float:
    return min(abs(theta - c) for c in GRADE_CUTS.values())


def population(n: int, rng: random.Random):
    """θ uniformly over the grade bands + 10% below-Junior; 20% overclaim their grade by one level."""
    people = []
    for i in range(n):
        band = rng.choices(["none", "junior", "middle", "senior"], weights=[0.1, 0.3, 0.33, 0.27])[0]
        lo, hi = {"none": (-2.2, -1.0), "junior": (-1.0, 0.0), "middle": (0.0, 1.0), "senior": (1.0, 2.3)}[band]
        theta = rng.uniform(lo, hi)
        tg = true_grade(theta)
        declared = "junior" if tg == "none" else tg
        if rng.random() < 0.2 and declared != "senior":
            declared = GRADES[GRADES.index(declared) + 1]
        people.append((i, theta, tg, declared))
    return people


def run(n: int, seed: int) -> dict:
    rng = random.Random(seed)
    report: dict = {"n_per_spec": n, "seed": seed, "test_length": LEN}
    labels = ["none", "junior", "middle", "senior"]
    all_true, all_pred, over, under, ntests, nflags = [], [], 0, 0, [], 0
    retest_a, retest_b, theta_a, theta_b = [], [], [], []
    grade_rt: list[tuple[str, str, float, float, float]] = []  # grade 1, grade 2, |θ − cut|, conf 1, conf 2
    scores_by_grade = {g: [] for g in labels}
    item_resp: dict[int, list[tuple[float, bool]]] = {}
    item_spec: dict[int, str] = {}
    per_spec = {}

    for spec in SPECS:
        bank = Bank(spec, random.Random(seed + 101 * SPECS.index(spec)))
        tp, pp = [], []
        for _, theta, tg, declared in population(n, rng):
            pred, out, k, f, seen = protocol(bank, declared, theta, rng)
            # the same profile goes through the whole procedure again, on forms it has not seen
            pred2, out2, _, _, _ = protocol(bank, declared, theta, rng, seen)
            grade_rt.append((pred, pred2, nearest_cut_distance(theta), out.confidence, out2.confidence))
            nflags += f
            tp.append(tg)
            pp.append(pred)
            ntests.append(k)
            scores_by_grade[tg].append(out.scaled_score)
            # test–retest on the declared grade: two independent forms
            f1, g1, o1 = take(bank, declared, theta, rng)
            f2, g2, o2 = take(bank, declared, theta, rng, {x.question_id for x in f1})
            retest_a.append(o1.passed or o1.flagged)
            retest_b.append(o2.passed or o2.flagged)
            theta_a.append(o1.theta)
            theta_b.append(o2.theta)
            total = sum(g.is_correct for g in g1)
            for it, g in zip(f1, g1, strict=True):
                key = it.question_id + 10000 * SPECS.index(spec)
                item_spec[key] = spec
                item_resp.setdefault(key, []).append((total - g.is_correct, g.is_correct))
        acc = mean(1.0 if a == b else 0.0 for a, b in zip(tp, pp, strict=True))
        per_spec[spec] = {"accuracy": round(acc, 3),
                          "weighted_kappa": round(cohen_kappa(tp, pp, labels, weighted=True), 3)}
        all_true += tp
        all_pred += pp
        rank = {g: i for i, g in enumerate(labels)}
        over += sum(1 for a, b in zip(tp, pp, strict=True) if rank[b] > rank[a])
        under += sum(1 for a, b in zip(tp, pp, strict=True) if rank[b] < rank[a])

    N = len(all_true)
    confusion = {t: {p: sum(1 for a, b in zip(all_true, all_pred, strict=True) if a == t and b == p)
                     for p in labels} for t in labels}
    report["classification"] = {
        "accuracy": round(mean(1.0 if a == b else 0.0 for a, b in zip(all_true, all_pred, strict=True)), 3),
        "weighted_kappa": round(cohen_kappa(all_true, all_pred, labels, weighted=True), 3),
        "over_graded_rate": round(over / N, 3),
        "under_graded_rate": round(under / N, 3),
        "within_one_grade": round(mean(1.0 if abs(labels.index(a) - labels.index(b)) <= 1 else 0.0
                                       for a, b in zip(all_true, all_pred, strict=True)), 3),
        "avg_tests_per_candidate": round(mean(ntests), 2),
        "honest_flag_rate": round(nflags / N, 3),
        "per_specialization": per_spec,
        "confusion": confusion,
    }
    report["test_retest"] = {
        "pass_fail_agreement": round(mean(1.0 if a == b else 0.0 for a, b in zip(retest_a, retest_b, strict=True)), 3),
        "kappa": round(cohen_kappa(retest_a, retest_b, [False, True]), 3),
        "theta_correlation": round(pearson(theta_a, theta_b), 3),
        "mean_abs_scaled_diff": round(mean(abs(scaled_score(a) - scaled_score(b))
                                           for a, b in zip(theta_a, theta_b, strict=True)), 2),
    }

    def agreement(rows):
        return round(mean(1.0 if a == b else 0.0 for a, b, *_ in rows), 3) if rows else None

    g1, g2 = [r[0] for r in grade_rt], [r[1] for r in grade_rt]
    far = [r for r in grade_rt if r[2] >= 0.25]
    near = [r for r in grade_rt if r[2] < 0.25]
    confident = [r for r in grade_rt if r[3] >= 0.8 and r[4] >= 0.8]
    report["grade_retest"] = {
        "n": len(grade_rt),
        "exact_agreement": agreement(grade_rt),
        "within_one_grade": round(mean(1.0 if abs(labels.index(a) - labels.index(b)) <= 1 else 0.0
                                       for a, b in zip(g1, g2, strict=True)), 3),
        "weighted_kappa": round(cohen_kappa(g1, g2, labels, weighted=True), 3),
        "agreement_far_from_cut": agreement(far), "share_far_from_cut": round(len(far) / len(grade_rt), 3),
        "agreement_near_cut": agreement(near),
        "agreement_both_confident": agreement(confident),
        "share_both_confident": round(len(confident) / len(grade_rt), 3),
        "confusion": {a: {b: sum(1 for x, y in zip(g1, g2, strict=True) if x == a and y == b) for b in labels}
                      for a in labels},
    }

    # ---- 3. form equivalence: blueprint vs naive random selection
    eq = {}
    for spec in SPECS:
        bank = Bank(spec, random.Random(seed))
        for grade in GRADES:
            bp_means, naive_means, bp_exp, naive_exp = [], [], [], []
            theta0 = GRADE_CUTS[grade] + 0.5
            for s in range(300):
                f = bank.form(grade, random.Random(s), exposure=False)
                bp_means.append(mean(x.b for x in f))
                bp_exp.append(mean(p_correct(theta0, *bank.true[x.question_id]) for x in f))
                lo = min(DIFFICULTY_PROFILE[grade])
                cand = [it for it in bank.items if it.difficulty >= lo]
                naive = random.Random(s).sample(cand, LEN)
                naive_means.append(mean(x.b for x in naive))
                naive_exp.append(mean(p_correct(theta0, *bank.true[x.id]) for x in naive))
            eq[f"{spec}/{grade}"] = {
                "blueprint_sd_nominal_b": round(stdev(bp_means), 3),
                "naive_sd_nominal_b": round(stdev(naive_means), 3),
                "blueprint_sd_expected_score": round(stdev(bp_exp), 3),
                "naive_sd_expected_score": round(stdev(naive_exp), 3),
            }
    report["form_equivalence"] = {
        "per_form": eq,
        "avg_blueprint_sd_expected_score": round(mean(v["blueprint_sd_expected_score"] for v in eq.values()), 3),
        "avg_naive_sd_expected_score": round(mean(v["naive_sd_expected_score"] for v in eq.values()), 3),
    }

    # ---- 4. discrimination
    rpb, upper_lower, rpb_by_spec = [], [], {sp: [] for sp in SPECS}
    for key, resp in item_resp.items():
        if len(resp) < 30:
            continue
        rest = [r for r, _ in resp]
        u = [1.0 if x else 0.0 for _, x in resp]
        if 0 < sum(u) < len(u):
            r_ = pearson(rest, u)
            rpb.append(r_)
            rpb_by_spec[item_spec[key]].append(r_)
            # classic upper–lower index: share correct in the top 27% minus the bottom 27% by rest score
            ranked = sorted(resp, key=lambda x: x[0])
            k27 = max(1, round(0.27 * len(ranked)))
            upper_lower.append(mean(1.0 if x else 0.0 for _, x in ranked[-k27:])
                               - mean(1.0 if x else 0.0 for _, x in ranked[:k27]))
    srt = sorted(rpb)
    jun, sen = scores_by_grade["junior"], scores_by_grade["senior"]
    mid = scores_by_grade["middle"]
    pooled = math.sqrt((stdev(jun) ** 2 + stdev(mid) ** 2) / 2)
    report["discrimination"] = {
        "items_evaluated": len(rpb),
        "mean_item_rest_correlation": round(mean(rpb), 3),
        "share_items_rpb_above_0_2": round(mean(1.0 if r > 0.2 else 0.0 for r in rpb), 3),
        "rpb_p10_p50_p90": [round(srt[int(q * (len(srt) - 1))], 3) for q in (0.1, 0.5, 0.9)],
        "mean_rpb_by_spec": {sp: round(mean(v), 3) for sp, v in rpb_by_spec.items() if v},
        "index_d_mean": round(mean(upper_lower), 3),
        "share_d_good": round(mean(1.0 if d >= 0.3 else 0.0 for d in upper_lower), 3),
        "share_d_fair": round(mean(1.0 if 0.2 <= d < 0.3 else 0.0 for d in upper_lower), 3),
        "share_d_review": round(mean(1.0 if d < 0.2 else 0.0 for d in upper_lower), 3),
        "auc_senior_vs_junior": round(auc(sen, jun), 3),
        "auc_middle_vs_junior": round(auc(mid, jun), 3),
        "cohen_d_middle_vs_junior": round((mean(mid) - mean(jun)) / pooled, 2) if pooled else None,
        "mean_scaled_score_by_true_grade": {g: round(mean(v), 1) for g, v in scores_by_grade.items() if v},
    }

    # ---- 5. leak resistance: junior-level person (θ = -0.4) memorised K leaked Middle forms
    leak = {}
    bank = Bank("backend", random.Random(seed))
    for k in (0, 1, 3, 10):
        fixed_p, gen_p, det_p, flagged = [], [], [], []
        for trial in range(300):
            r = random.Random(trial * 31 + k)
            known: set[int] = set()
            for j in range(k):
                known |= {x.question_id for x in bank.form("middle", random.Random(10_000 + trial * 50 + j),
                                                           exposure=False)}
            # (a) one fixed test for everybody: a single leaked copy reveals every answer
            fixed = bank.form("middle", random.Random(1), exposure=False)
            g = answer(fixed, -0.4, bank, r, known={x.question_id for x in fixed} if k else None)
            fo = grade_attempt(g, "middle")
            fixed_p.append(fo.passed or fo.flagged)
            # (b) generated parallel forms, detector ignored
            _, _, out = take(bank, "middle", -0.4, r, known=known)
            gen_p.append(out.passed or out.flagged)
            # (c) generated forms + leakage detector + one confirmation form
            out2, _, fl = take_with_confirmation(bank, "middle", -0.4, r, known=known)
            det_p.append(out2.passed)
            flagged.append(fl)
        leak[f"leaked_forms_{k}"] = {
            "pass_rate_single_fixed_test": round(mean(fixed_p), 3),
            "pass_rate_generated_forms": round(mean(gen_p), 3),
            "pass_rate_generated_plus_detector": round(mean(det_p), 3),
            "flagged_share": round(mean(1.0 if f else 0.0 for f in flagged), 3),
        }
    report["leak_resistance"] = {"candidate_true_theta": -0.4, "target": "middle", "results": leak}

    # ---- 7. reliability vs test length (parallel forms, Backend/Middle)
    rel = {}
    for length in (10, 15, 20, 25):
        ta, tb, agree = [], [], []
        b2 = Bank("backend", random.Random(seed))
        for _ in range(300):
            theta = rng.uniform(-1.0, 2.0)
            f1, _, o1 = take(b2, "middle", theta, rng, length=length)
            _, _, o2 = take(b2, "middle", theta, rng, {x.question_id for x in f1}, length=length)
            ta.append(o1.theta)
            tb.append(o2.theta)
            agree.append(1.0 if (o1.passed or o1.flagged) == (o2.passed or o2.flagged) else 0.0)
        rel[str(length)] = {"theta_correlation": round(pearson(ta, tb), 3),
                            "pass_fail_agreement": round(mean(agree), 3)}
    report["reliability_by_length"] = rel

    # ---- 6. calibration: recover true b from responses given estimated abilities
    bank = Bank("backend", random.Random(seed))
    resp_by_item: dict[int, list[tuple[float, bool]]] = {}
    for _ in range(1500):
        theta = rng.gauss(0.3, 1.0)
        grade = "junior" if theta < -0.3 else ("middle" if theta < 0.9 else "senior")
        form, graded, out = take(bank, grade, theta, rng)
        for it, g in zip(form, graded, strict=True):
            resp_by_item.setdefault(it.question_id, []).append((out.theta, g.is_correct))
    nominal, recovered, truth = [], [], []
    for it in bank.items:
        data = resp_by_item.get(it.id, [])
        if len(data) < 40:
            continue
        a, b_true, c = bank.true[it.id]
        best, best_ll = it.b, -1e18
        for step in range(-60, 61):
            b = step / 20
            ll = sum(math.log(max(1e-9, p_correct(t, it.a, b, it.c) if u else 1 - p_correct(t, it.a, b, it.c)))
                     for t, u in data)
            if ll > best_ll:
                best, best_ll = b, ll
        nominal.append(it.b)
        recovered.append(best)
        truth.append(b_true)
    report["integrity"] = integrity_simulation(seed)
    report["speed"] = speed(seed)
    report["calibration"] = {
        "items_calibrated": len(truth),
        "corr_nominal_vs_true_b": round(pearson(nominal, truth), 3),
        "corr_recovered_vs_true_b": round(pearson(recovered, truth), 3),
        "rmse_nominal": round(math.sqrt(mean((a - b) ** 2 for a, b in zip(nominal, truth, strict=True))), 3),
        "rmse_recovered": round(math.sqrt(mean((a - b) ** 2 for a, b in zip(recovered, truth, strict=True))), 3),
    }
    return report


def _simulate_behaviour(bank, form, theta, rng, kind, known):
    """Answers + client events for one attempt. Response time: expected time of the item × lognormal
    noise. kind: honest | lookup (searches for answers it does not know) | preknowledge (memorised leak)."""
    traces, graded = [], []
    ev = ClientEvents(focus_lost=_poisson(rng, 0.5), copies=_poisson(rng, 0.05))
    ev.away_ms = sum(int(rng.uniform(5, 40) * 1000) for _ in range(ev.focus_lost))
    for it in form:
        a, b, c = bank.true[it.question_id]
        p = p_correct(theta, a, b, c)
        exp_s = expected_seconds(it.qtype, it.difficulty)
        t = exp_s * math.exp(rng.gauss(0, 0.45))
        pasted = False
        if kind == "preknowledge" and it.question_id in known and not it.family:
            ok, t = True, exp_s * rng.uniform(0.08, 0.2)
        elif kind == "lookup" and p < 0.6 and rng.random() < 0.75:
            ok = rng.random() < 0.9
            away = rng.uniform(30, 120)
            ev.focus_lost += 1
            ev.away_ms += int(away * 1000)
            ev.copies += rng.random() < 0.6
            pasted = it.qtype == "numeric" and rng.random() < 0.5
        else:
            ok = rng.random() < p
        traces.append(ItemTrace(it.qtype, it.difficulty, it.a, it.b, it.c, ok, int(t * 1000), pasted,
                                it.family is not None))
        graded.append(GradedItem(it.competency, it.a, it.b, it.c, ok, 1.0 if ok else 0.0, it.family is not None))
    return traces, graded, ev


def _poisson(rng, lam):
    k, p, threshold = 0, 1.0, math.exp(-lam)
    while True:
        p *= rng.random()
        if p <= threshold:
            return k
        k += 1


def integrity_simulation(seed: int, n: int = 400) -> dict:
    """Junior-level people (θ ∈ [−0.7, −0.1]) take the Middle test: honestly, looking answers up
    elsewhere, or with memorised answers of 3 leaked forms. Honest Middle-level people (θ ∈ [0.2, 1.2])
    measure false positives where it matters — on candidates who pass."""
    rng = random.Random(seed + 500)
    bank = Bank("backend", random.Random(seed))
    out = {}
    for kind in ("honest_strong", "honest_weak", "lookup", "preknowledge"):
        risk, attention, passed_plain, passed_checked = [], [], [], []
        for trial in range(n):
            theta = rng.uniform(0.2, 1.2) if kind == "honest_strong" else rng.uniform(-0.7, -0.1)
            known: set[int] = set()
            if kind == "preknowledge":
                for j in range(3):
                    known |= {x.question_id for x in bank.form("middle", random.Random(90_000 + trial * 7 + j),
                                                               exposure=False)}
            form = bank.form("middle", rng, exposure=False)
            behaviour = "honest" if kind.startswith("honest") else kind
            traces, graded, ev = _simulate_behaviour(bank, form, theta, rng, behaviour, known)
            res = grade_attempt(graded, "middle")
            total_ms = sum(t.time_ms for t in traces) + ev.away_ms
            integ = assess(traces, res.theta, ev, total_ms)
            risk.append(integ.level == "risk")
            attention.append(integ.level == "attention")
            passed_plain.append(res.passed)
            passed_checked.append(res.passed and integ.level != "risk")
        out[kind] = {"risk_rate": round(mean(1.0 if x else 0.0 for x in risk), 3),
                     "attention_rate": round(mean(1.0 if x else 0.0 for x in attention), 3),
                     "pass_rate_leak_detector_only": round(mean(1.0 if x else 0.0 for x in passed_plain), 3),
                     "pass_rate_with_behaviour_check": round(mean(1.0 if x else 0.0 for x in passed_checked), 3)}
    return out


def speed(seed: int) -> dict:
    """Wall-clock cost of the testing engine operations (pure Python, one core)."""
    bank = Bank("backend", random.Random(seed))
    rng = random.Random(seed)
    t0 = time.perf_counter()
    forms = [bank.form("middle", rng, exposure=False) for _ in range(200)]
    t1 = time.perf_counter()
    graded = [answer(f, 0.3, bank, rng) for f in forms]
    t2 = time.perf_counter()
    for g in graded:
        grade_attempt(g, "middle")
    t3 = time.perf_counter()
    return {"generate_form_ms": round((t1 - t0) * 1000 / 200, 2), "grade_attempt_ms": round((t3 - t2) * 1000 / 200, 2)}


def markdown(r: dict) -> str:
    c, t, d, e = r["classification"], r["test_retest"], r["discrimination"], r["form_equivalence"]
    lines = [
        "# Валидация механики тестирования",
        "",
        f"Синтетическая популяция: {r['n_per_spec']} кандидатов на каждую из 4 специализаций, seed={r['seed']}, "
        f"длина теста {r['test_length']}. Ответы симулируются с «истинными» параметрами заданий, отличающимися "
        "от номинальных (b + N(0;0,35), a·LogN(0;0,2)) — оценка не круговая.",
        "",
        "## 1. Классификация грейда",
        table(["Метрика", "Значение"], [
            ["Точность (грейд = истинный)", c["accuracy"]],
            ["Взвешенная κ Коэна", c["weighted_kappa"]],
            ["Точность ±1 грейд", c["within_one_grade"]],
            ["Доля завышения грейда", c["over_graded_rate"]],
            ["Доля занижения грейда", c["under_graded_rate"]],
            ["Тестов на кандидата (с учётом теста ниже)", c["avg_tests_per_candidate"]],
        ]),
        "",
        table(["Специализация", "Точность", "Взвеш. κ"],
              [[k, v["accuracy"], v["weighted_kappa"]] for k, v in c["per_specialization"].items()]),
        "",
        "Матрица ошибок (строки — истинный грейд, столбцы — подтверждённый):",
        "",
        table(["истинный \\ итог"] + list(c["confusion"]),
              [[k] + list(v.values()) for k, v in c["confusion"].items()]),
        "",
        "## 2. Тест–ретест (две независимые параллельные формы)",
        table(["Метрика", "Значение"], [
            ["Согласие «сдал/не сдал»", t["pass_fail_agreement"]],
            ["κ Коэна", t["kappa"]],
            ["Корреляция θ между формами", t["theta_correlation"]],
            ["Средняя \\|Δ\\| шкального балла", t["mean_abs_scaled_diff"]],
        ]),
        "",
        "### 2а. Повторное прохождение всей процедуры одним профилем",
        "",
        "Каждый синтетический кандидат дважды проходит полную процедуру (тест на заявленный грейд → при "
        "неудаче тест ниже → подтверждающая форма при флаге), во второй раз — на заданиях, которых он ещё "
        "не видел. Сравниваются присвоенные грейды.",
        "",
        table(["Метрика", "Значение"], [
            ["Совпадение присвоенного грейда", r["grade_retest"]["exact_agreement"]],
            ["В пределах ±1 грейда", r["grade_retest"]["within_one_grade"]],
            ["Взвешенная κ между прохождениями", r["grade_retest"]["weighted_kappa"]],
            [f"Совпадение, если θ дальше 0,25 от порога (доля таких {r['grade_retest']['share_far_from_cut']})",
             r["grade_retest"]["agreement_far_from_cut"]],
            ["Совпадение у пограничных (\\|θ − порог\\| < 0,25)", r["grade_retest"]["agreement_near_cut"]],
            [f"Совпадение, если оба результата уверенные ≥ 0,8 (доля {r['grade_retest']['share_both_confident']})",
             r["grade_retest"]["agreement_both_confident"]],
        ]),
        "",
        "Матрица: строки — грейд после первого прохождения, столбцы — после второго:",
        "",
        table(["1-е \\ 2-е"] + list(r["grade_retest"]["confusion"]),
              [[k] + list(v.values()) for k, v in r["grade_retest"]["confusion"].items()]),
        "",
        "## 3. Эквивалентность форм",
        "Разброс (SD) ожидаемой доли верных ответов кандидата на пороге грейда по 300 формам:",
        "",
        table(["Форма", "Blueprint", "Случайный отбор"],
              [[k, v["blueprint_sd_expected_score"], v["naive_sd_expected_score"]] for k, v in e["per_form"].items()]),
        "",
        f"Среднее: blueprint **{e['avg_blueprint_sd_expected_score']}** vs случайный отбор "
        f"**{e['avg_naive_sd_expected_score']}**.",
        "",
        "## 4. Дискриминативность",
        table(["Метрика", "Значение"], [
            ["Средняя корреляция задание–остаток (r_pb)", d["mean_item_rest_correlation"]],
            ["Доля заданий с r_pb > 0,2", d["share_items_rpb_above_0_2"]],
            ["r_pb: 10-й / 50-й / 90-й перцентиль", " / ".join(str(x) for x in d["rpb_p10_p50_p90"])],
            ["Индекс D (верхние 27% − нижние 27%), среднее", d["index_d_mean"]],
            ["Задания с D ≥ 0,3 (хорошо разделяют)", d["share_d_good"]],
            ["Задания с D 0,2–0,3 (приемлемо)", d["share_d_fair"]],
            ["Задания с D < 0,2 (на пересмотр)", d["share_d_review"]],
            ["AUC Senior vs Junior", d["auc_senior_vs_junior"]],
            ["AUC Middle vs Junior", d["auc_middle_vs_junior"]],
            ["d Коэна Middle vs Junior", d["cohen_d_middle_vs_junior"]],
        ]),
        "",
        "Средний шкальный балл по истинному грейду: " + ", ".join(
            f"{k}: {v}" for k, v in d["mean_scaled_score_by_true_grade"].items()),
        "",
        "## 5. Устойчивость к утечке заданий",
        "Кандидат уровня Junior (θ = −0,4) заранее выучил ответы K «слитых» вариантов теста Middle:",
        "",
        table(["K слитых вариантов", "Единый тест", "Генерируемые формы", "Формы + детектор утечки",
               "Доля помеченных"],
              [[k.split("_")[-1], v["pass_rate_single_fixed_test"], v["pass_rate_generated_forms"],
                v["pass_rate_generated_plus_detector"], v["flagged_share"]]
               for k, v in r["leak_resistance"]["results"].items()]),
        "",
        f"Ложные срабатывания детектора на честных кандидатах: **{r['classification']['honest_flag_rate']}** "
        "(им предлагается одна подтверждающая форма, грейд не теряется).",
        "",
        "Средняя r_pb по специализациям: " + ", ".join(f"{k}: {v}" for k, v in d["mean_rpb_by_spec"].items()) + ".",
        "",
        "## 5а. Проверка честности по поведению",
        "",
        "Модель времени ответа: ожидаемое время задания × логнормальный шум. «Ищет ответы» — на незнакомых "
        "вопросах уходит со вкладки, копирует вопрос, вставляет числовой ответ. «Знает слитые ответы» — "
        "выучил 3 варианта и отвечает на их статические задания быстро и верно. Уровень Junior "
        "(θ ∈ [−0,7; −0,1]) проходит тест Middle; ложные срабатывания — на честных Middle (θ ∈ [0,2; 1,2]).",
        "",
        table(["Группа", "Риск (нужна подтверждающая форма)", "Замечания", "Сдали: только детектор утечки",
               "Сдали: + проверка поведения"],
              [[{"honest_strong": "Честные, уровень Middle", "honest_weak": "Честные, уровень Junior",
                 "lookup": "Ищут ответы на стороне", "preknowledge": "Знают слитые ответы"}[k],
                v["risk_rate"], v["attention_rate"], v["pass_rate_leak_detector_only"],
                v["pass_rate_with_behaviour_check"]] for k, v in r["integrity"].items()]),
        "",
        "## 6. Надёжность в зависимости от длины теста",
        table(["Заданий", "Корреляция θ (параллельные формы)", "Согласие «сдал/не сдал»"],
              [[k, v["theta_correlation"], v["pass_fail_agreement"]] for k, v in r["reliability_by_length"].items()]),
        "",
        "## 7. Калибровка банка по ответам",
        table(["Метрика", "Номинальные b", "Перекалиброванные b"], [
            ["Корреляция с истинными b", r["calibration"]["corr_nominal_vs_true_b"],
             r["calibration"]["corr_recovered_vs_true_b"]],
            ["RMSE", r["calibration"]["rmse_nominal"], r["calibration"]["rmse_recovered"]],
        ]),
        "",
        "## 9. Скорость",
        "",
        f"Генерация индивидуального варианта: **{r['speed']['generate_form_ms']} мс**, оценка попытки (EAP, "
        f"person-fit, детектор утечки): **{r['speed']['grade_attempt_ms']} мс** — на одном ядре, без БД.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400, help="synthetic candidates per specialization")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    t0 = time.time()
    rep = run(args.n, args.seed)
    rep["runtime_sec"] = round(time.time() - t0, 1)
    md = markdown(rep)
    save("tests_report", rep, md)
    print(md)
    print(f"\nSaved to evaluation/results/tests_report.(json|md) in {rep['runtime_sec']} s")
