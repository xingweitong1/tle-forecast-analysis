"""
误差增长律拟合：幂律、指数、二次多项式。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy import stats


def _power_law(t, a, b):
  return a * np.power(t, b)


def _exponential(t, a, b, c):
  return a * np.exp(b * t) + c


def _polynomial2(t, a, b, c):
  return a * t ** 2 + b * t + c


def fit_growth_laws(days: np.ndarray, errors: np.ndarray) -> dict:
  """
  对 (days, median/mean errors) 拟合多种增长律，返回 AIC 最优模型。
  """
  days = np.asarray(days, dtype=float)
  errors = np.asarray(errors, dtype=float)
  mask = (days > 0) & (errors > 0) & np.isfinite(errors)
  days, errors = days[mask], errors[mask]

  if len(days) < 2:
    return {}

  results = {}

  # 二次多项式
  try:
    coeffs = np.polyfit(days, errors, min(2, len(days) - 1))
    pred = np.poly1d(coeffs)(days)
    rss = np.sum((errors - pred) ** 2)
    k = len(coeffs)
    aic = len(days) * np.log(rss / len(days) + 1e-12) + 2 * k
    results["polynomial"] = {
      "params": coeffs.tolist(),
      "formula": f"y = {coeffs[0]:.4f}*t^2 + {coeffs[1]:.4f}*t + {coeffs[2]:.4f}",
      "aic": aic,
      "predict": lambda t: np.poly1d(coeffs)(t),
    }
  except (np.linalg.LinAlgError, ValueError):
    pass

  # 幂律 y = a·t^b
  if len(days) >= 2:
    try:
      popt, _ = curve_fit(_power_law, days, errors, p0=[1.0, 1.0], maxfev=5000)
      pred = _power_law(days, *popt)
      rss = np.sum((errors - pred) ** 2)
      aic = len(days) * np.log(rss / len(days) + 1e-12) + 2 * 2
      results["power_law"] = {
        "params": popt.tolist(),
        "formula": f"y = {popt[0]:.4f}·t^{popt[1]:.4f}",
        "aic": aic,
        "growth_exponent": float(popt[1]),
        "predict": lambda t, p=popt: _power_law(t, *p),
      }
    except (RuntimeError, ValueError):
      pass

  # 指数
  if len(days) >= 3:
    try:
      popt, _ = curve_fit(
        _exponential, days, errors,
        p0=[errors[0], 0.3, 0.0], maxfev=10000,
        bounds=([0, 0, -np.inf], [np.inf, 5, np.inf]),
      )
      pred = _exponential(days, *popt)
      rss = np.sum((errors - pred) ** 2)
      aic = len(days) * np.log(rss / len(days) + 1e-12) + 2 * 3
      results["exponential"] = {
        "params": popt.tolist(),
        "formula": f"y = {popt[0]:.4f}·exp({popt[1]:.4f}·t) + {popt[2]:.4f}",
        "aic": aic,
        "predict": lambda t, p=popt: _exponential(t, *p),
      }
    except (RuntimeError, ValueError):
      pass

  if results:
    best = min(results, key=lambda k: results[k]["aic"])
    results["best_model"] = best
    results["best_aic"] = results[best]["aic"]

  return results


def summarize_by_orbit_day(df: pd.DataFrame) -> pd.DataFrame:
  """按轨道类型和预报天数汇总统计量。"""
  summary = (
    df.groupby(["Orbit", "Day"])["Error_km"]
    .agg(
      count="count",
      mean="mean",
      median="median",
      std="std",
      q25=lambda x: x.quantile(0.25),
      q75=lambda x: x.quantile(0.75),
    )
    .reset_index()
  )
  return summary


def growth_rate_analysis(df: pd.DataFrame) -> dict:
  """分轨道类型拟合增长律。"""
  results = {}
  for orbit in df["Orbit"].unique():
    sub = df[df["Orbit"] == orbit]
    medians = sub.groupby("Day")["Error_km"].median()
    days = medians.index.values.astype(float)
    errs = medians.values.astype(float)
    fits = fit_growth_laws(days, errs)
    results[orbit] = {
      "days": days.tolist(),
      "medians": errs.tolist(),
      "fits": fits,
    }
  return results
