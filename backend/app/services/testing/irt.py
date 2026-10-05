"""Item Response Theory (3PL) primitives and EAP ability estimation.

Why IRT: two candidates receive *different* forms, so a raw "% correct" is not comparable between
them (one form may be slightly harder). IRT puts items and people on one latent scale θ: the
ability estimate accounts for which items were answered, so results of different forms are
directly comparable (test equating "for free" once items are calibrated).
"""

import math
from dataclasses import dataclass

D = 1.7  # scaling constant: makes the logistic curve close to the normal ogive
GRID = [round(-4.0 + 0.05 * i, 2) for i in range(161)]


def p_correct(theta: float, a: float, b: float, c: float) -> float:
    return c + (1.0 - c) / (1.0 + math.exp(-D * a * (theta - b)))


def item_information(theta: float, a: float, b: float, c: float) -> float:
    p = p_correct(theta, a, b, c)
    q = 1 - p
    if p <= 0 or q <= 0:
        return 0.0
    return (D * a) ** 2 * (q / p) * ((p - c) / (1 - c)) ** 2


@dataclass
class Posterior:
    theta: float
    se: float
    weights: list[float]  # normalised posterior mass over GRID

    def p_above(self, cut: float) -> float:
        return sum(w for t, w in zip(GRID, self.weights, strict=True) if t >= cut)


def eap(responses: list[tuple[float, float, float, bool]], prior_mean: float = 0.0,
        prior_sd: float = 1.25) -> Posterior:
    """Expected-a-posteriori estimate of θ.

    responses: (a, b, c, is_correct) per administered item. Unanswered items must be passed as
    incorrect by the caller. EAP is finite even for all-correct/all-wrong patterns (unlike MLE).
    """
    log_post = []
    for t in GRID:
        lp = -0.5 * ((t - prior_mean) / prior_sd) ** 2
        for a, b, c, u in responses:
            p = min(max(p_correct(t, a, b, c), 1e-9), 1 - 1e-9)
            lp += math.log(p if u else 1 - p)
        log_post.append(lp)
    m = max(log_post)
    w = [math.exp(x - m) for x in log_post]
    s = sum(w)
    w = [x / s for x in w]
    mean = sum(t * x for t, x in zip(GRID, w, strict=True))
    var = sum((t - mean) ** 2 * x for t, x in zip(GRID, w, strict=True))
    return Posterior(theta=mean, se=math.sqrt(var), weights=w)


def scaled_score(theta: float) -> int:
    """Public 0–100 scale: 25 / 50 / 75 correspond to Junior / Middle / Senior cut-points."""
    return max(0, min(100, round(50 + 25 * theta)))
