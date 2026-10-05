"""Strength of the FSP signal for a given specialization.

Absence of FSP history is NOT a zero: `summarize()` returns `available=False`, and the matching
engine then uses a neutral baseline for this component (no penalty). Any verified participation
can only add to the profile.
"""

import math
from dataclasses import dataclass, field
from datetime import date

LEVEL_WEIGHT = {"international": 1.0, "all_russian": 0.85, "interregional": 0.6, "regional": 0.45}
LEVEL_NAMES = {
    "international": "международные",
    "all_russian": "всероссийские",
    "interregional": "межрегиональные",
    "regional": "региональные",
}
RANK_BONUS = {"МС": 0.6, "КМС": 0.4, "I разряд": 0.25, "II разряд": 0.12, "III разряд": 0.06}

# Relevance of a discipline (and team role) to the platform specialization.
DISCIPLINE_RELEVANCE = {
    "Продуктовое программирование": {"backend": 0.8, "frontend": 0.8, "data_ml": 0.7, "devops": 0.6},
    "Алгоритмическое программирование": {"backend": 0.8, "frontend": 0.5, "data_ml": 0.75, "devops": 0.4},
    "Программирование систем информационной безопасности": {"backend": 0.6, "frontend": 0.3,
                                                            "data_ml": 0.3, "devops": 0.9},
    "Программирование беспилотных авиационных систем": {"backend": 0.5, "frontend": 0.2,
                                                        "data_ml": 0.6, "devops": 0.4},
    "Программирование робототехники": {"backend": 0.5, "frontend": 0.2, "data_ml": 0.6, "devops": 0.4},
}
ROLE_SPEC = {"backend": "backend", "frontend": "frontend", "ml": "data_ml", "devops": "devops",
             "data": "data_ml"}


@dataclass
class AchievementLike:
    event_name: str
    discipline: str
    level: str
    date: date
    place: int | None
    participants_total: int | None
    role: str | None
    specialization_hint: str | None


@dataclass
class FSPSummary:
    available: bool
    strength: float = 0.0          # 0..1, relevance-weighted to the specialization
    count: int = 0
    prizes: int = 0
    best_text: str | None = None
    sport_rank: str | None = None
    highlights: list[str] = field(default_factory=list)


def place_factor(place: int | None, total: int | None) -> float:
    if place is None:
        return 0.25  # participation
    if place == 1:
        return 1.0
    if place == 2:
        return 0.85
    if place == 3:
        return 0.75
    if total and place / total <= 0.1:
        return 0.55
    if total and place / total <= 0.3:
        return 0.4
    return 0.25


def relevance(a: AchievementLike, specialization: str) -> float:
    if a.role and ROLE_SPEC.get(a.role.lower()) == specialization:
        return 1.0
    if a.specialization_hint == specialization:
        return 0.95
    return DISCIPLINE_RELEVANCE.get(a.discipline, {}).get(specialization, 0.4)


def achievement_points(a: AchievementLike, specialization: str, today: date) -> float:
    years = max(0.0, (today - a.date).days / 365.25)
    recency = 0.5 ** (years / 2.5)
    return LEVEL_WEIGHT.get(a.level, 0.4) * place_factor(a.place, a.participants_total) * recency \
        * relevance(a, specialization)


def describe(a: AchievementLike) -> str:
    place = f"{a.place} место" if a.place else "участник"
    return f"{place} — {a.event_name} ({a.date.year})"


def summarize(achievements: list[AchievementLike] | None, specialization: str, today: date,
              sport_rank: str | None = None) -> FSPSummary:
    if not achievements:
        return FSPSummary(available=False, sport_rank=sport_rank)
    pts = sum(achievement_points(a, specialization, today) for a in achievements)
    pts += RANK_BONUS.get(sport_rank or "", 0.0)
    strength = 1 - math.exp(-pts / 1.2)
    best = max(achievements, key=lambda a: achievement_points(a, specialization, today))
    prizes = sum(1 for a in achievements if a.place and a.place <= 3)
    top = sorted(achievements, key=lambda a: -achievement_points(a, specialization, today))[:3]
    return FSPSummary(
        available=True,
        strength=round(strength, 3),
        count=len(achievements),
        prizes=prizes,
        best_text=describe(best),
        sport_rank=sport_rank,
        highlights=[describe(a) for a in top],
    )
