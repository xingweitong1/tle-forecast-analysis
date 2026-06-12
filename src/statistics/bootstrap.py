"""
Bootstrap 置信区间：百分位法 + BCa 法。
Gaussian vs Bootstrap 对比。
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from config import BOOTSTRAP_N, CONFIDENCE_LEVEL


def _bootstrap_means(data: np.ndarray, n_boot: int) -> np.ndarray:
  n = len(data)
  idx = np.random.randint(0, n, size=(n_boot, n))
  samples = data[idx]
  return np.mean(samples, axis=1)


def bootstrap_percentile_ci(
  data: np.ndarray,
  stat_func=np.mean,
  n_boot: int = BOOTSTRAP_N,
  confidence: float = CONFIDENCE_LEVEL,
) -> tuple[float, float, float]:
  """百分位 Bootstrap 置信区间。"""
  n = len(data)
  boot_stats = np.empty(n_boot)
  for b in range(n_boot):
    sample = np.random.choice(data, size=n, replace=True)
    boot_stats[b] = stat_func(sample)
  alpha = (1 - confidence) / 2
  lower = np.percentile(boot_stats, alpha * 100)
  upper = np.percentile(boot_stats, (1 - alpha) * 100)
  return float(stat_func(data)), float(lower), float(upper)


def bootstrap_bca_ci(
  data: np.ndarray,
  stat_func=np.mean,
  n_boot: int = BOOTSTRAP_N,
  confidence: float = CONFIDENCE_LEVEL,
) -> tuple[float, float, float]:
  """
  BCa (Bias-Corrected accelerated) Bootstrap 置信区间。
  """
  data = np.asarray(data, dtype=float)
  n = len(data)
  theta_hat = stat_func(data)

  boot_stats = np.empty(n_boot)
  for b in range(n_boot):
    sample = np.random.choice(data, size=n, replace=True)
    boot_stats[b] = stat_func(sample)

  # bias correction z0
  prop_less = np.mean(boot_stats < theta_hat)
  prop_less = np.clip(prop_less, 1e-6, 1 - 1e-6)
  z0 = stats.norm.ppf(prop_less)

  # acceleration a (jackknife)
  jack = np.empty(n)
  for i in range(n):
    jack[i] = stat_func(np.delete(data, i))
  jack_mean = np.mean(jack)
  num = np.sum((jack_mean - jack) ** 3)
  den = 6.0 * (np.sum((jack_mean - jack) ** 2) ** 1.5 + 1e-12)
  a = num / den if den != 0 else 0.0

  alpha = (1 - confidence) / 2
  z_alpha = stats.norm.ppf(alpha)
  z_1alpha = stats.norm.ppf(1 - alpha)

  def _bca_quantile(z_alpha_val):
    num_z = z0 + z_alpha_val
    denom = 1 - a * num_z
    if abs(denom) < 1e-12:
      denom = 1e-12
    adj = z0 + num_z / denom
    return stats.norm.cdf(adj)

  lower_pct = _bca_quantile(z_alpha) * 100
  upper_pct = _bca_quantile(z_1alpha) * 100
  lower_pct = np.clip(lower_pct, 0.1, 99.9)
  upper_pct = np.clip(upper_pct, 0.1, 99.9)

  lower = np.percentile(boot_stats, lower_pct)
  upper = np.percentile(boot_stats, upper_pct)
  return float(theta_hat), float(lower), float(upper)


def gaussian_ci(
  data: np.ndarray,
  confidence: float = CONFIDENCE_LEVEL,
) -> tuple[float, float, float]:
  """正态理论置信区间（均值）。"""
  n = len(data)
  mean_val = np.mean(data)
  z = stats.norm.ppf(1 - (1 - confidence) / 2)
  se = np.std(data, ddof=1) / np.sqrt(n)
  return float(mean_val), float(mean_val - z * se), float(mean_val + z * se)


def bootstrap_ci(
  data: np.ndarray,
  method: str = "both",
  confidence: float = CONFIDENCE_LEVEL,
  n_boot: int = BOOTSTRAP_N,
) -> dict:
  """统一接口：返回 percentile 与 BCa 结果。"""
  data = np.asarray(data, dtype=float)
  data = data[~np.isnan(data)]
  if len(data) < 5:
    return {}

  result = {}
  if method in ("percentile", "both"):
    m, lo, hi = bootstrap_percentile_ci(data, n_boot=n_boot, confidence=confidence)
    result["percentile"] = {"estimate": m, "lower": lo, "upper": hi}
  if method in ("bca", "both"):
    m, lo, hi = bootstrap_bca_ci(data, n_boot=n_boot, confidence=confidence)
    result["bca"] = {"estimate": m, "lower": lo, "upper": hi}
  return result


def compare_gaussian_bootstrap(
  data: np.ndarray,
  confidence: float = CONFIDENCE_LEVEL,
  n_boot: int = BOOTSTRAP_N,
) -> dict:
  """Gaussian vs Bootstrap（百分位 + BCa）全面对比。"""
  data = np.asarray(data, dtype=float)
  data = data[~np.isnan(data)]
  g_mean, g_lo, g_hi = gaussian_ci(data, confidence)
  boot = bootstrap_ci(data, method="both", confidence=confidence, n_boot=n_boot)

  return {
    "n": len(data),
    "sample_mean": float(np.mean(data)),
    "sample_median": float(np.median(data)),
    "gaussian": {"estimate": g_mean, "lower": g_lo, "upper": g_hi, "width": g_hi - g_lo},
    "bootstrap_percentile": boot.get("percentile", {}),
    "bootstrap_bca": boot.get("bca", {}),
    "skewness": float(stats.skew(data)),
    "kurtosis": float(stats.kurtosis(data)),
  }
