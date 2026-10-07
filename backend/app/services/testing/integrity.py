"""Behavioural integrity check of a test attempt (cheating detection).

The leak detector in scoring.py looks at WHAT was answered (person-fit, static vs parametric items).
This module looks at HOW it was answered — signals the web client reports with every answer, in the
open (the candidate is told what is recorded; no camera, no screen capture):

  * leaving the test tab (count and total time away) — looking answers up elsewhere;
  * pasting into an answer field and copying the question text — moving text to/from a search engine
    or an LLM;
  * fast correct answers on items that are hard FOR THIS CANDIDATE: P(correct | θ_ref) is low, yet the
    answer came in a fraction of the time such an item takes. That is the response-time signature of
    pre-knowledge (memorised leaked answers), see van der Linden & Guo (2008). θ_ref is estimated on the
    parametric items only — their answers cannot be memorised, so a leak does not inflate it.

Risk points add up into a level: ok / attention / risk. A «risk» result is not rejected: like a leak
flag it needs one confirmation form (policy.py), and the candidate sees what was noticed. Nothing is
inferred from a single signal: one tab switch or one fast answer is normal behaviour.
"""

from dataclasses import dataclass, field

from app.services.testing.irt import eap, p_correct

# expected answering time, seconds: by item type, scaled by difficulty 1..5
BASE_SECONDS = {"single": 35.0, "multi": 50.0, "numeric": 60.0}
FAST_SHARE = 0.25          # «fast» = under a quarter of the expected time
HARD_FOR_PERSON = 0.35     # P(correct | θ_ref) below this — the item is hard for this candidate
FAST_ATTENTION = 2         # fast correct answers to hard items: a remark …
FAST_RISK = 4              # … and on its own a reason to confirm the result


@dataclass
class ItemTrace:
    qtype: str
    difficulty: int
    a: float
    b: float
    c: float
    is_correct: bool
    time_ms: int | None = None
    pasted: bool = False
    is_family: bool = False   # parametric (leak-proof) item


@dataclass
class ClientEvents:
    focus_lost: int = 0
    away_ms: int = 0
    copies: int = 0


@dataclass
class Integrity:
    level: str                       # ok | attention | risk
    points: int
    signals: dict = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)  # codes: focus, away, paste, copy, fast_correct

    def to_dict(self) -> dict:
        return {"level": self.level, "points": self.points, "signals": self.signals, "reasons": self.reasons}


def expected_seconds(qtype: str, difficulty: int) -> float:
    return BASE_SECONDS.get(qtype, 45.0) * (0.8 + 0.1 * difficulty)


def reference_theta(items: list[ItemTrace], theta: float) -> float:
    """Ability on the leak-proof (parametric) items; the overall estimate when there are too few."""
    fam = [(it.a, it.b, it.c, it.is_correct) for it in items if it.is_family]
    return eap(fam).theta if len(fam) >= 3 else theta


def fast_correct_count(items: list[ItemTrace], theta: float) -> int:
    """Fast correct answers to static items that are hard at the reference ability `theta`."""
    n = 0
    for it in items:
        if not it.is_correct or it.time_ms is None or it.is_family:
            continue
        hard = p_correct(theta, it.a, it.b, it.c) < HARD_FOR_PERSON
        fast = it.time_ms / 1000 < FAST_SHARE * expected_seconds(it.qtype, it.difficulty)
        n += hard and fast
    return n


def assess(items: list[ItemTrace], theta: float, events: ClientEvents, duration_ms: int | None) -> Integrity:
    points, reasons = 0, []
    # the attempt's span: wall-clock duration, but never less than the time actually spent on items + away
    span = max(duration_ms or 0, sum(it.time_ms or 0 for it in items) + events.away_ms)
    away_share = events.away_ms / span if span else 0.0
    pastes = sum(1 for it in items if it.pasted)
    theta_ref = reference_theta(items, theta)
    fast = fast_correct_count(items, theta_ref)

    if events.focus_lost >= 8:
        points, reasons = points + 2, [*reasons, "focus"]
    elif events.focus_lost >= 3:
        points, reasons = points + 1, [*reasons, "focus"]
    if away_share >= 0.25:
        points, reasons = points + 1, [*reasons, "away"]
    if pastes >= 3:
        points, reasons = points + 2, [*reasons, "paste"]
    elif pastes >= 1:
        points, reasons = points + 1, [*reasons, "paste"]
    if events.copies >= 2:
        points, reasons = points + 1, [*reasons, "copy"]
    if fast >= FAST_RISK:
        points, reasons = points + 3, [*reasons, "fast_correct"]
    elif fast >= FAST_ATTENTION:
        points, reasons = points + 1, [*reasons, "fast_correct"]

    level = "risk" if points >= 3 else "attention" if points >= 1 else "ok"
    signals = {"focus_lost": events.focus_lost, "away_share": round(away_share, 3), "pastes": pastes,
               "copies": events.copies, "fast_correct": fast, "theta_ref": round(theta_ref, 3),
               "timed_items": sum(1 for it in items if it.time_ms is not None)}
    return Integrity(level, points, signals, reasons)
