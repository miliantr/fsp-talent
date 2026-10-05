"""Who may take which test and when (grade change rules and cooldowns).

Rules (configurable through settings):
  * one active attempt at a time;
  * the same (specialization, target grade) can be retaken only after RETAKE_COOLDOWN_DAYS —
    protects against memorising the bank by brute force;
  * a candidate without a verified grade may immediately take a test for a lower grade after
    failing a higher one (the grade is never lowered forcibly, the profile is never blocked);
  * a verified grade changes at most once per GRADE_CHANGE_COOLDOWN_DAYS (grade_locked_until),
    except the fast track: a confident result (upgrade_eligible) unlocks the next grade test at once;
  * re-confirming the current grade is allowed after the retake cooldown and refreshes the profile.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.catalog import GRADE_NAMES, GRADE_RANK
from app.i18n import t


@dataclass
class AttemptRecord:
    specialization: str
    target_grade: str
    finished_at: datetime | None
    in_progress: bool
    flagged: bool = False


@dataclass
class CandidateGradeState:
    verified_specialization: str | None
    verified_grade: str | None
    grade_locked_until: datetime | None
    upgrade_eligible: bool


@dataclass
class Eligibility:
    grade: str
    allowed: bool
    kind: str  # initial | fallback | reconfirm | upgrade | change | confirm | blocked
    reason: str | None = None
    available_at: datetime | None = None


def check_eligibility(state: CandidateGradeState, history: list[AttemptRecord], specialization: str,
                      target: str, now: datetime, retake_days: int) -> Eligibility:
    if any(h.in_progress for h in history):
        return Eligibility(target, False, "blocked", t("test.policy.finish_current"))

    last_same = max(
        (h.finished_at for h in history
         if h.finished_at and h.specialization == specialization and h.target_grade == target),
        default=None,
    )
    same = [h for h in history if h.finished_at and h.specialization == specialization and h.target_grade == target]
    same.sort(key=lambda h: h.finished_at)
    if same and same[-1].flagged and not (len(same) > 1 and same[-2].flagged):
        # a flagged (possibly leaked) result is confirmed by ONE fresh form, available immediately;
        # a second flagged result in a row falls back to the regular cooldown
        return Eligibility(target, True, "confirm")
    if last_same and now < last_same + timedelta(days=retake_days):
        until = last_same + timedelta(days=retake_days)
        return Eligibility(
            target, False, "blocked",
            t("test.policy.retake_after", grade=GRADE_NAMES[target], date={"date": until.isoformat()}), until,
        )

    verified = state.verified_grade if state.verified_specialization == specialization else None
    if state.verified_grade and state.verified_specialization != specialization:
        # switching specialization changes the category -> same lock as a grade change
        if state.grade_locked_until and now < state.grade_locked_until:
            return Eligibility(
                target, False, "blocked",
                t("test.policy.change_after", date={"date": state.grade_locked_until.isoformat()}),
                state.grade_locked_until,
            )
        return Eligibility(target, True, "change")

    if verified is None:
        failed_higher = any(
            h.finished_at and h.specialization == specialization
            and GRADE_RANK[h.target_grade] > GRADE_RANK[target] for h in history
        )
        return Eligibility(target, True, "fallback" if failed_higher else "initial")

    diff = GRADE_RANK[target] - GRADE_RANK[verified]
    if diff == 0:
        return Eligibility(target, True, "reconfirm")
    locked = state.grade_locked_until is not None and now < state.grade_locked_until
    if diff == 1 and state.upgrade_eligible:
        return Eligibility(target, True, "upgrade")
    if locked:
        return Eligibility(
            target, False, "blocked",
            t("test.policy.grade_locked", date={"date": state.grade_locked_until.isoformat()}),
            state.grade_locked_until,
        )
    return Eligibility(target, True, "upgrade" if diff > 0 else "change")
