# Poster outline

Use only the numbers in `experiments/reports/assurance-v1/summary.json` and the plots in `experiments/reports/assurance-v1/plots/`.

## Title

VERIFORGE 1.0.0: a small arithmetic check, not a new decision procedure

## Question

Does a larger concrete test catch more bad rewrites than a 10-input test, on a frozen held-out set?

## Method

- Grammar: `+`, `-`, `*`, integers or unsigned wrap.
- Labels: polynomial identity, or exhaustive search when `2^(width × variables) ≤ 65,536`.
- 463 pairs, 27 families, held-out by whole family.
- Protocol time: 2026-10-11 16:43:36 UTC.

## Result panel

- Testing misses: 0/54 at every budget. Hypothesis: not supported.
- Plot: `experiments/reports/assurance-v1/plots/testing-false-equivalence.svg`.
- Mode traps: 16/16 pairs differ by mode.
- Z3 4.8.17 and CVC5 1.3.2: same 463 statuses. Bitwuzla 0.8.2 matches on unsigned pairs only.
- Seeded faults: 10/10 on fixtures.

## Cost panel

- Testing wall time about 0.004 s at budget 10 and 4.78 s at budget 10,000.
- Evaluator medians under about 4 microseconds on the scaling grid.
- Plot: `experiments/reports/assurance-v1/plots/execution-time-medians.svg`.
- Do not draw a speedup arrow from a shorter expression.

## Limits

Shared Python integers. No SMT numbers. Two pairs over the exhaustive budget. Not a new algorithm.
