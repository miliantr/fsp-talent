"""Calibrated item bank.

Initial IRT parameters come from expert difficulty levels (1..5) and the item format. They are the
"prior calibration"; `evaluation/evaluate_tests.py` shows how they are re-estimated from response
data (Rasch/JML) once real answers accumulate.
"""

from app.domain.question_bank import advanced, backend, data_ml, devops, frontend
from app.domain.question_bank.families import FAMILIES as BASE_FAMILIES
from app.domain.question_bank.families import Family
from app.domain.question_bank.families_extra import EXTRA_FAMILIES

FAMILIES: list[Family] = BASE_FAMILIES + EXTRA_FAMILIES
FAMILY_BY_CODE = {f.code: f for f in FAMILIES}

# Expert difficulty level -> IRT difficulty b (logit scale, centred on the Middle cut-point).
DIFFICULTY_TO_B = {1: -2.0, 2: -1.0, 3: 0.0, 4: 1.0, 5: 2.0}
DISCRIMINATION = {"single": 1.0, "multi": 1.3, "numeric": 1.4}

_PREFIX = {"backend": "BE", "frontend": "FE", "data_ml": "ML", "devops": "DO"}


def guessing(qtype: str, n_options: int) -> float:
    if qtype == "single":
        return round(0.8 / max(n_options, 2), 3)  # candidates rarely guess uniformly
    if qtype == "multi":
        return 0.05
    return 0.0


def bank_items() -> list[dict]:
    """All static + parametric items as plain dicts ready to be stored."""
    out: list[dict] = []
    for spec, items in (("backend", backend.ITEMS + advanced.BACKEND),
                        ("frontend", frontend.ITEMS + advanced.FRONTEND),
                        ("data_ml", data_ml.ITEMS + advanced.DATA_ML),
                        ("devops", devops.ITEMS + advanced.DEVOPS)):
        counters: dict[str, int] = {}
        for comp, diff, text, options, correct in items:
            counters[comp] = counters.get(comp, 0) + 1
            qtype = "multi" if isinstance(correct, list) else "single"
            out.append({
                "code": f"{_PREFIX[spec]}-{comp.split('_', 1)[1].upper()}-{counters[comp]:02d}",
                "specialization_id": spec,
                "competency_id": comp,
                "difficulty": diff,
                "qtype": qtype,
                "text": text,
                "options": options,
                "correct": correct if isinstance(correct, list) else [correct],
                "family": None,
                "irt_a": DISCRIMINATION[qtype],
                "irt_b": DIFFICULTY_TO_B[diff],
                "irt_c": guessing(qtype, len(options)),
            })
    for fam in FAMILIES:
        out.append({
            "code": fam.code,
            "specialization_id": fam.specialization,
            "competency_id": fam.competency,
            "difficulty": fam.difficulty,
            "qtype": fam.qtype,
            "text": f"[Параметрическое семейство] {fam.title}",
            "options": [],
            "correct": [],
            "family": fam.code,
            "irt_a": DISCRIMINATION[fam.qtype],
            "irt_b": DIFFICULTY_TO_B[fam.difficulty],
            "irt_c": guessing(fam.qtype, 4),
        })
    return out


__all__ = ["DIFFICULTY_TO_B", "FAMILIES", "FAMILY_BY_CODE", "Family", "bank_items", "guessing"]
