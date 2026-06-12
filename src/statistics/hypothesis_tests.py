"""
轨道类型差异检验：ANOVA + Kruskal-Wallis。
在每个预报时长上分别检验 LEO / MEO / GEO 差异。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def _check_normality(groups: list[np.ndarray]) -> bool:
  """Shapiro-Wilk 正态性（每组 n<=5000）。"""
  for g in groups:
    if len(g) < 8:
      return False
    sample = g if len(g) <= 5000 else np.random.choice(g, 5000, replace=False)
    _, p = stats.shapiro(sample)
    if p < 0.05:
      return False
  return True


def run_orbit_comparison_tests(df: pd.DataFrame) -> pd.DataFrame:
  """
  对每个预报天数 Day，检验三轨道类型误差分布差异。
  返回 ANOVA 与 Kruskal-Wallis 结果表。
  """
  orbits = sorted(df["Orbit"].unique())
  days = sorted(df["Day"].unique())
  rows = []

  for day in days:
    groups = [
      df[(df["Orbit"] == o) & (df["Day"] == day)]["Error_km"].dropna().values
      for o in orbits
    ]
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 2:
      continue

    normal_ok = _check_normality(groups)

    # ANOVA
    if all(len(g) >= 2 for g in groups):
      f_stat, p_anova = stats.f_oneway(*groups)
    else:
      f_stat, p_anova = np.nan, np.nan

    # Kruskal-Wallis
    if all(len(g) >= 1 for g in groups):
      h_stat, p_kw = stats.kruskal(*groups)
    else:
      h_stat, p_kw = np.nan, np.nan

    rows.append({
      "Day": day,
      "n_groups": len(groups),
      "group_sizes": [len(g) for g in groups],
      "normal_assumption": normal_ok,
      "recommended_test": "ANOVA" if normal_ok else "Kruskal-Wallis",
      "anova_F": f_stat,
      "anova_p": p_anova,
      "kruskal_H": h_stat,
      "kruskal_p": p_kw,
      "significant_0.05": p_kw < 0.05 if not np.isnan(p_kw) else False,
    })

  return pd.DataFrame(rows)
