"""Matching engine configuration: component weights and presets.

Default ("balanced") weights — rationale (see docs/matching.md):
  skills 0.28  — the employer describes a need mostly as a stack; but skills are weighted by
                 *evidence* (confirmed by test competencies), not by keyword presence;
  test   0.20  — objective, comparable (IRT) measure of competence relative to the required grade;
  grade  0.16  — category fit; over-qualification is acceptable, under-qualification is not;
  spec   0.10  — mostly a gate (unrelated specializations are excluded), adjacent ones get partial;
  fsp    0.10  — verified competition record; neutral baseline when absent (never a penalty);
  fresh  0.06  — recently active / re-confirmed profiles respond to offers more often;
  salary 0.05  — candidate's expectation vs the offered range (salary is mandatory on our side);
  exp    0.03  — formal experience: deliberately small, the CV is self-declared;
  format 0.02  — remote / office / hybrid compatibility.
"""

import json
from functools import lru_cache

from app.core.config import get_settings

ENGINE_VERSION = "1.2"

COMPONENTS = ["skills", "test", "grade", "specialization", "fsp", "freshness", "salary",
              "experience", "format"]

# Display labels of components and presets are localized: app.i18n ("ref.component.*", "ref.preset.*").

PRESETS: dict[str, dict[str, float]] = {
    "balanced": {"skills": 0.26, "test": 0.16, "grade": 0.22, "specialization": 0.10, "fsp": 0.10,
                 "freshness": 0.06, "salary": 0.05, "experience": 0.03, "format": 0.02},
    "skills_first": {"skills": 0.40, "test": 0.18, "grade": 0.14, "specialization": 0.10, "fsp": 0.05,
                     "freshness": 0.05, "salary": 0.04, "experience": 0.02, "format": 0.02},
    "proven_talent": {"skills": 0.20, "test": 0.30, "grade": 0.12, "specialization": 0.08, "fsp": 0.18,
                      "freshness": 0.06, "salary": 0.03, "experience": 0.02, "format": 0.01},
}
# Neutral value of the FSP component when the candidate has no FSP history.
FSP_NEUTRAL = 0.3
# Freshness half-life in days.
FRESHNESS_HALF_LIFE_DAYS = 120

# Prior competency score assumed for a declared skill that no test competency covers.
UNVERIFIED_SKILL_PRIOR = 0.5


@lru_cache
def _override() -> dict:
    raw = get_settings().matching_weights_json
    return json.loads(raw) if raw else {}


def get_weights(preset: str | None) -> dict[str, float]:
    weights = dict(PRESETS.get(preset or "balanced", PRESETS["balanced"]))
    weights.update({k: float(v) for k, v in _override().items() if k in weights})
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}
