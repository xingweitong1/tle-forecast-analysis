#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TLE 预报精度统计分析 — 主程序

优先使用仓库内已下载的 Space-Track TLE 缓存；
若缓存不完整且配置了凭证，则自动补下载。
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
  sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config import (
  FORECAST_DAYS,
  ORBIT_SATELLITES,
  OUTPUT_DIR,
  PROCESSED_DIR,
  SPACETRACK_PASSWORD,
  SPACETRACK_USER,
  date_range_utc,
)
from src.download.spacetrack import download_all_satellites, load_cached_spacetrack_paths
from src.propagation.sgp4_error import build_error_dataset
from src.statistics.bootstrap import compare_gaussian_bootstrap
from src.statistics.covariance import simplified_covariance_1d, theoretical_vs_observed_variance
from src.statistics.growth_fit import growth_rate_analysis, summarize_by_orbit_day
from src.statistics.hypothesis_tests import run_orbit_comparison_tests
from src.visualization.plots import generate_all_plots


def _count_cached(paths: dict) -> int:
  return sum(len(v) for v in paths.values())


def _expected_count() -> int:
  return sum(len(v) for v in ORBIT_SATELLITES.values())


def load_spacetrack_data(force_download: bool = False) -> tuple[pd.DataFrame, str]:
  """加载 TLE：优先本地缓存，必要时从 Space-Track 下载。"""
  expected = _expected_count()
  cached = load_cached_spacetrack_paths(ORBIT_SATELLITES)
  n_cached = _count_cached(cached)

  if not force_download and n_cached == expected:
    print(f"[本地缓存] 使用已下载 TLE：{n_cached}/{expected} 颗卫星")
    paths = cached
    source = "spacetrack (本地缓存 TLE, 20260313-20260611)"
  else:
    if not SPACETRACK_USER or not SPACETRACK_PASSWORD:
      if n_cached > 0:
        print(f"[警告] 缓存不完整 ({n_cached}/{expected})，且未设置 Space-Track 凭证。")
        print("将使用已有缓存继续分析。")
        paths = cached
        source = f"spacetrack (部分本地缓存, {n_cached}颗)"
      else:
        print("错误：无本地 TLE 缓存，且未设置 Space-Track 凭证。")
        print("请设置 SPACETRACK_USER / SPACETRACK_PASSWORD，或使用 --local 指定缓存目录。")
        sys.exit(1)
    else:
      start, end = date_range_utc()
      print(f"[下载] Space-Track: {start.date()} ~ {end.date()}，共 {expected} 颗卫星")
      paths = download_all_satellites(ORBIT_SATELLITES, start, end)
      if _count_cached(paths) == 0:
        paths = load_cached_spacetrack_paths(ORBIT_SATELLITES)
      source = "spacetrack (3个月历史 TLE)"

  if not paths or _count_cached(paths) == 0:
    print("错误：无可用 TLE 文件。")
    sys.exit(1)

  df = build_error_dataset(paths)
  if df.empty:
    print("错误：TLE 配对不足，无法计算误差。")
    sys.exit(1)

  df.to_csv(PROCESSED_DIR / "errors_raw.csv", index=False)
  return df, source


def run_statistics_pipeline(df: pd.DataFrame) -> dict:
  """完整统计方法链。"""
  np.random.seed(42)
  results = {}

  summary = summarize_by_orbit_day(df)
  results["summary"] = summary

  print("\n" + "=" * 50)
  print(" 预报误差统计汇总 (km)")
  print("=" * 50)
  pivot = summary.pivot(index="Orbit", columns="Day", values="median")
  print(pivot.round(2).to_string())
  print("=" * 50)

  cov_results = []
  for day in FORECAST_DAYS:
    all_err = df[df["Day"] == day]["Error_km"].dropna().values
    if len(all_err) > 1:
      cov_results.append(theoretical_vs_observed_variance(all_err, day))
      theory = simplified_covariance_1d(day)
      print(f"\n[协方差传播] {day}天: 观测方差={cov_results[-1]['observed_variance']:.4f}, "
            f"理论简化方差={theory:.4f}")
  results["covariance"] = cov_results

  growth = growth_rate_analysis(df)
  results["growth"] = growth
  print("\n[误差增长律拟合]")
  for orbit, info in growth.items():
    fits = info.get("fits", {})
    best = fits.get("best_model", "N/A")
    if best != "N/A" and best in fits:
      print(f"  {orbit}: 最优模型={best}, {fits[best].get('formula', '')}")

  ci_by_group = {}
  ci_report = []
  for orbit in df["Orbit"].unique():
    for day in FORECAST_DAYS:
      sub = df[(df["Orbit"] == orbit) & (df["Day"] == day)]["Error_km"].dropna().values
      if len(sub) < 10:
        continue
      ci = compare_gaussian_bootstrap(sub)
      ci_by_group[(orbit, day)] = ci
      ci_report.append({"Orbit": orbit, "Day": day, **{
        "gauss_lo": ci["gaussian"]["lower"], "gauss_hi": ci["gaussian"]["upper"],
        "boot_pct_lo": ci.get("bootstrap_percentile", {}).get("lower"),
        "boot_pct_hi": ci.get("bootstrap_percentile", {}).get("upper"),
        "boot_bca_lo": ci.get("bootstrap_bca", {}).get("lower"),
        "boot_bca_hi": ci.get("bootstrap_bca", {}).get("upper"),
        "skewness": ci["skewness"],
      }})
      if day == 7 and orbit == "LEO":
        print(f"\n[Gaussian vs Bootstrap] {orbit} {day}天:")
        print(f"  Gaussian 95% CI: [{ci['gaussian']['lower']:.2f}, {ci['gaussian']['upper']:.2f}] km")
        bp = ci.get("bootstrap_percentile", {})
        bb = ci.get("bootstrap_bca", {})
        if bp:
          print(f"  Bootstrap Percentile: [{bp['lower']:.2f}, {bp['upper']:.2f}] km")
        if bb:
          print(f"  Bootstrap BCa: [{bb['lower']:.2f}, {bb['upper']:.2f}] km")
        print(f"  偏度={ci['skewness']:.2f} → {'非正态，Bootstrap更可靠' if abs(ci['skewness']) > 0.5 else '近似对称'}")

  results["ci_by_group"] = ci_by_group
  results["ci_report"] = pd.DataFrame(ci_report)

  tests = run_orbit_comparison_tests(df)
  results["hypothesis_tests"] = tests
  print("\n[轨道类型差异检验]")
  for _, row in tests.iterrows():
    rec = row["recommended_test"]
    p = row["anova_p"] if rec == "ANOVA" else row["kruskal_p"]
    sig = "显著" if row["significant_0.05"] else "不显著"
    print(f"  {int(row['Day'])}天: {rec} p={p:.2e} → 组间差异{sig}")

  return results


def save_report(df: pd.DataFrame, results: dict, data_source: str) -> None:
  """保存 CSV 与 JSON 报告。"""
  df.to_csv(PROCESSED_DIR / "errors_all.csv", index=False)
  results["summary"].to_csv(PROCESSED_DIR / "summary_by_orbit_day.csv", index=False)
  if "ci_report" in results and not results["ci_report"].empty:
    results["ci_report"].to_csv(PROCESSED_DIR / "confidence_intervals.csv", index=False)
  results["hypothesis_tests"].to_csv(PROCESSED_DIR / "hypothesis_tests.csv", index=False)

  report = {
    "data_source": data_source,
    "n_samples": len(df),
    "forecast_days": FORECAST_DAYS,
    "median_errors": results["summary"].to_dict(orient="records"),
    "growth_best_models": {
      o: info.get("fits", {}).get("best_model")
      for o, info in results.get("growth", {}).items()
    },
    "hypothesis_tests": results["hypothesis_tests"].to_dict(orient="records"),
  }
  (OUTPUT_DIR / "report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2, default=str),
    encoding="utf-8",
  )

  plot_paths = generate_all_plots(
    df, results["summary"], results["growth"],
    results.get("ci_by_group", {}), OUTPUT_DIR,
  )
  print(f"\n[输出] 图表已保存至 {OUTPUT_DIR}:")
  for p in plot_paths:
    print(f"  - {p.name}")


def main():
  parser = argparse.ArgumentParser(description="TLE 预报精度统计分析")
  parser.add_argument(
    "--download",
    action="store_true",
    help="强制从 Space-Track 重新下载（需凭证）",
  )
  args = parser.parse_args()

  np.random.seed(42)
  print("=" * 60)
  print(" TLE 预报精度研究 — 三轨道类型统计比较")
  print(" 数据来源：Space-Track 历史 TLE")
  print("=" * 60)

  df, source = load_spacetrack_data(force_download=args.download)
  print(f"\n数据来源: {source}")
  print(f"有效样本数: {len(df)}")

  results = run_statistics_pipeline(df)
  save_report(df, results, source)
  print("\n完成。请查看 output/ 目录中的图表与 report.json。")


if __name__ == "__main__":
  main()
