"""Small-sample statistics used by the assurance experiment.

Wilson intervals and bootstrap median intervals are deterministic given the
recorded seed. They do not remove systematic label error.
"""

from __future__ import annotations

import math
import random
import statistics
from typing import Sequence

# Quantile of the standard normal used for a 95% two-sided interval.
Z_95 = 1.959963984540054


def wilson_interval(successes: int, trials: int, *, z: float = Z_95) -> tuple[float, float] | None:
    """95% Wilson score interval for a binomial proportion.

    ``successes`` is the event count and ``trials`` is the denominator.
    Returns ``None`` when the denominator is zero.
    """

    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("successes must lie in 0..trials")
    if trials == 0:
        return None
    phat = successes / trials
    z2 = z * z
    denom = 1.0 + z2 / trials
    center = (phat + z2 / (2.0 * trials)) / denom
    margin = z * math.sqrt((phat * (1.0 - phat) / trials) + z2 / (4.0 * trials * trials)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def bootstrap_median_interval(
    values: Sequence[float],
    *,
    seed: int,
    resamples: int = 2000,
) -> dict[str, float | int | None]:
    """Percentile bootstrap interval for the sample median."""

    if resamples < 100:
        raise ValueError("resamples must be at least 100")
    if not values:
        return {
            "n": 0,
            "median": None,
            "low": None,
            "high": None,
            "resamples": resamples,
            "seed": seed,
        }
    ordered = [float(value) for value in values]
    point = float(statistics.median(ordered))
    rng = random.Random(seed)
    n = len(ordered)
    medians = []
    for _ in range(resamples):
        sample = [ordered[rng.randrange(n)] for _ in range(n)]
        medians.append(statistics.median(sample))
    medians.sort()
    low_index = int(0.025 * (resamples - 1))
    high_index = int(0.975 * (resamples - 1))
    return {
        "n": n,
        "median": point,
        "low": float(medians[low_index]),
        "high": float(medians[high_index]),
        "resamples": resamples,
        "seed": seed,
    }


def rank(values: Sequence[float]) -> list[float]:
    """Average ranks, 1-based, with ties averaged."""

    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        average = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = average
        i = j + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Spearman rank correlation. ``None`` if undefined."""

    if len(xs) != len(ys) or len(xs) < 2:
        return None
    rx = rank(xs)
    ry = rank(ys)
    mean_x = sum(rx) / len(rx)
    mean_y = sum(ry) / len(ry)
    num = sum((a - mean_x) * (b - mean_y) for a, b in zip(rx, ry))
    den_x = math.sqrt(sum((a - mean_x) ** 2 for a in rx))
    den_y = math.sqrt(sum((b - mean_y) ** 2 for b in ry))
    if den_x == 0.0 or den_y == 0.0:
        return None
    return num / (den_x * den_y)


def percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        raise ValueError("empty sample")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight
