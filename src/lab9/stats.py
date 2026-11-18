"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb
from numbers import Integral

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError("labels must be paired")
    counts = dict.fromkeys(("tp", "fp", "fn", "tn"), 0)
    for h, j in zip(human, judge):
        if h not in ("PASS", POS) or j not in ("PASS", POS):
            raise ValueError("expected PASS or FAIL")
        counts[("t" if h == j else "f") + ("p" if j == POS else "n")] += 1
    return counts


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    c = confusion(human, judge)
    tp, fp, fn = c["tp"], c["fp"], c["fn"]
    return tp / (tp + fp) if tp + fp else 0.0, tp / (tp + fn) if tp + fn else 0.0


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    c = confusion(human, judge)
    tp, fp, fn, tn = (c[key] for key in ("tp", "fp", "fn", "tn"))
    n = len(human)
    expected = (tp + fn) * (tp + fp) + (tn + fp) * (tn + fn)
    if n * n == expected:
        raise ValueError("kappa is undefined")
    return ((tp + tn) * n - expected) / (n * n - expected)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    if not all(0 <= rate <= 1 for rate in (observed_rate, sensitivity, specificity)):
        raise ValueError("rates must be in [0, 1]")
    signal = sensitivity + specificity - 1
    if signal <= 0:
        raise ValueError("judge must perform above chance")
    return max(0.0, min(1.0, (observed_rate + specificity - 1) / signal))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    if len(a) != len(b) or not len(a):
        raise ValueError("bootstrap requires nonempty paired samples")
    delta = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    if not np.isfinite(delta).all():
        raise ValueError("bootstrap requires finite samples")
    mean = float(delta.mean())
    if np.all(delta == delta[0]):
        return mean, mean, mean
    ci = bootstrap((a, b), lambda x, y, axis: np.mean(x - y, axis=axis),
                   paired=True, method="percentile", n_resamples=n_resamples,
                   confidence_level=confidence, rng=np.random.default_rng(rng)).confidence_interval
    return mean, float(ci.low), float(ci.high)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_trials(n, c, k)
    return (comb(n, k) - comb(n - c, k)) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_trials(n, c, k)
    return comb(c, k) / comb(n, k)


def _validate_trials(n: int, c: int, k: int) -> None:
    if any(isinstance(v, bool) or not isinstance(v, Integral) for v in (n, c, k)):
        raise ValueError("trial counts must be integers")
    if not (1 <= k <= n and 0 <= c <= n):
        raise ValueError("require 1 <= k <= n and 0 <= c <= n")
