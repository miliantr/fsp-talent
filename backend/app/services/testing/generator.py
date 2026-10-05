"""Blueprint-driven generation of parallel test forms.

A form is NOT a fixed list of questions and NOT free-form AI generation. It is built from:
  1. a deterministic blueprint for (specialization, target grade): how many items per competency
     and which difficulty level every slot has — identical for every candidate;
  2. a random draw of a calibrated item for each slot from a large bank, with exposure control
     (rarely shown items are preferred) and exclusion of items the candidate has already seen;
  3. randomised presentation: item order, option order and fresh parameters for parametric
     families.

Every candidate therefore gets a different form with the same structure and the same expected
difficulty, and IRT scoring makes the remaining small differences irrelevant.
"""

import random
from dataclasses import dataclass, field

from app.domain.question_bank import FAMILY_BY_CODE

# Share of each difficulty level (1..5) in a form, by target grade. The mass is concentrated
# around the decision cut-points of the grade (max test information where the decision is made).
DIFFICULTY_PROFILE: dict[str, dict[int, float]] = {
    "junior": {1: 0.20, 2: 0.40, 3: 0.33, 4: 0.07},
    "middle": {2: 0.20, 3: 0.40, 4: 0.33, 5: 0.07},
    "senior": {3: 0.25, 4: 0.45, 5: 0.30},
}


@dataclass
class ItemSpec:
    id: int
    code: str
    specialization: str
    competency: str
    difficulty: int
    qtype: str
    text: str
    options: list
    correct: list
    family: str | None
    a: float
    b: float
    c: float
    exposure: int = 0


@dataclass
class FormItem:
    question_id: int
    code: str
    position: int
    competency: str
    difficulty: int
    qtype: str
    text: str
    options: list
    correct: list
    a: float
    b: float
    c: float
    params: dict = field(default_factory=dict)
    family: str | None = None


@dataclass
class Blueprint:
    specialization: str
    target_grade: str
    length: int
    competency_quota: dict[str, int]
    difficulty_counts: dict[int, int]
    slots: list[tuple[str, int]]  # (competency, difficulty) per slot

    def to_dict(self) -> dict:
        return {
            "specialization": self.specialization,
            "target_grade": self.target_grade,
            "length": self.length,
            "competency_quota": self.competency_quota,
            "difficulty_counts": {str(k): v for k, v in self.difficulty_counts.items()},
        }


def _apportion(shares: dict, total: int, minimum: int = 0) -> dict:
    """Largest-remainder apportionment of `total` seats according to `shares`."""
    keys = list(shares)
    norm = sum(shares.values())
    raw = {k: shares[k] / norm * total for k in keys}
    out = {k: max(minimum, int(raw[k])) for k in keys}
    while sum(out.values()) < total:
        k = max(keys, key=lambda k: raw[k] - out[k])
        out[k] += 1
    while sum(out.values()) > total:
        k = max((k for k in keys if out[k] > minimum), key=lambda k: out[k] - raw[k])
        out[k] -= 1
    return out


def build_blueprint(specialization: str, target_grade: str, competency_weights: dict[str, float],
                    length: int) -> Blueprint:
    quota = _apportion(competency_weights, length, minimum=1)
    diff_counts = _apportion(DIFFICULTY_PROFILE[target_grade], length)
    difficulties = sorted(d for d, n in diff_counts.items() for _ in range(n))
    # Spread difficulties across competencies (Sainte-Laguë over the sorted difficulty list), so
    # each competency gets easy and hard items — deterministic, identical for all candidates.
    assigned = {c: 0 for c in quota}
    slots: list[tuple[str, int]] = []
    for d in difficulties:
        comp = max(
            (c for c in quota if assigned[c] < quota[c]),
            key=lambda c: (quota[c] / (2 * assigned[c] + 1), quota[c]),
        )
        assigned[comp] += 1
        slots.append((comp, d))
    return Blueprint(specialization, target_grade, length, quota, diff_counts, slots)


# Parametric families cannot be leaked (every draw is a new variant), so they are preferred and
# are not subject to exposure control.
FAMILY_WEIGHT = 3.0


def _pick(candidates: list[ItemSpec], rng: random.Random) -> ItemSpec:
    # Exposure control: probability inversely proportional to how often a static item was shown.
    weights = [FAMILY_WEIGHT if it.family else 1.0 / (1.0 + it.exposure) for it in candidates]
    return rng.choices(candidates, weights=weights, k=1)[0]


def select_items(blueprint: Blueprint, pool: list[ItemSpec], rng: random.Random,
                 seen_ids: set[int] | None = None) -> list[tuple[ItemSpec, int]]:
    """Fill every blueprint slot with an item. Returns (item, slot difficulty)."""
    seen_ids = seen_ids or set()
    by_cell: dict[tuple[str, int], list[ItemSpec]] = {}
    for it in pool:
        by_cell.setdefault((it.competency, it.difficulty), []).append(it)

    used: set[int] = set()
    chosen: list[tuple[ItemSpec, int]] = []
    drift = 0  # accumulated (chosen difficulty - planned difficulty), kept close to 0
    for comp, diff in blueprint.slots:
        pick = None
        for allow_seen in (False, True):
            # nearest difficulty first; on ties go in the direction that cancels the drift
            for delta in (0, 1, 2, 3, 4):
                order = [0] if delta == 0 else ([-delta, delta] if drift > 0 else [delta, -delta])
                for sgn in order:
                    cell = by_cell.get((comp, diff + sgn), [])
                    cands = [
                        it for it in cell
                        if it.id not in used and (allow_seen or it.id not in seen_ids or it.family)
                    ]
                    if cands:
                        pick = _pick(cands, rng)
                        drift += pick.difficulty - diff
                        break
                if pick:
                    break
            if pick:
                break
        if pick is None:
            raise ValueError(f"Item bank has no items for competency {comp}")
        used.add(pick.id)
        chosen.append((pick, diff))
    return chosen


def render_item(item: ItemSpec, position: int, rng: random.Random) -> FormItem:
    if item.family:
        fam = FAMILY_BY_CODE[item.family]
        r = fam.render(rng)
        return FormItem(item.id, item.code, position, item.competency, item.difficulty, item.qtype,
                        r["text"], r["options"], r["correct"], item.a, item.b, item.c, r["params"], item.family)
    order = list(range(len(item.options)))
    rng.shuffle(order)
    options = [item.options[i] for i in order]
    correct = sorted(order.index(i) for i in item.correct)
    return FormItem(item.id, item.code, position, item.competency, item.difficulty, item.qtype,
                    item.text, options, correct, item.a, item.b, item.c, {"option_order": order})


def generate_form(blueprint: Blueprint, pool: list[ItemSpec], rng: random.Random,
                  seen_ids: set[int] | None = None) -> list[FormItem]:
    chosen = select_items(blueprint, pool, rng, seen_ids)
    rng.shuffle(chosen)
    return [render_item(it, pos, rng) for pos, (it, _) in enumerate(chosen)]
