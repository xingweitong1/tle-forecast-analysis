"""可视化：误差增长、置信区间对比、文献对标。"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import LITERATURE_BENCHMARK, OUTPUT_DIR

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def plot_error_growth(df: pd.DataFrame, growth_results: dict, out_dir: Path) -> Path:
  """三轨道误差增长律拟合图。"""
  orbits = ["LEO", "MEO", "GEO"]
  colors = {"LEO": "red", "MEO": "green", "GEO": "blue"}
  days = sorted(df["Day"].unique())
  summary = df.groupby(["Orbit", "Day"])["Error_km"].median().unstack(level=0)

  fig, ax = plt.subplots(figsize=(10, 6), dpi=120)
  x_fit = np.linspace(0.5, 7.5, 50)

  for orbit in orbits:
    if orbit not in summary.columns:
      continue
    medians = summary[orbit].reindex(days).values
    ax.scatter(days, medians, color=colors[orbit], s=80, zorder=5, label=f"{orbit} 中位数")

    gr = growth_results.get(orbit, {})
    fits = gr.get("fits", {})
    best = fits.get("best_model")
    if best and best in fits:
      pred = fits[best]["predict"](x_fit)
      formula = fits[best].get("formula", best)
      ax.plot(x_fit, pred, color=colors[orbit], linestyle="--", linewidth=2,
              label=f"{orbit} 拟合 ({best})")

  ax.set_title("TLE 预报位置误差增长律：LEO vs MEO vs GEO", fontsize=14, fontweight="bold")
  ax.set_xlabel("预报时长 (天)")
  ax.set_ylabel("位置误差中位数 (km)")
  ax.set_xticks(days)
  ax.legend(loc="upper left", fontsize=9)
  ax.grid(True, linestyle="--", alpha=0.6)
  fig.tight_layout()
  path = out_dir / "error_growth_by_orbit.png"
  fig.savefig(path, bbox_inches="tight")
  plt.close(fig)
  return path


def plot_ci_comparison(ci_results: dict, orbit: str, day: int, out_dir: Path) -> Path:
  """Gaussian vs Bootstrap 置信区间对比柱状图。"""
  fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
  methods = []
  lowers, uppers, estimates = [], [], []

  g = ci_results.get("gaussian", {})
  if g:
    methods.append("Gaussian")
    estimates.append(g["estimate"])
    lowers.append(g["lower"])
    uppers.append(g["upper"])

  bp = ci_results.get("bootstrap_percentile", {})
  if bp:
    methods.append("Bootstrap\n(Percentile)")
    estimates.append(bp["estimate"])
    lowers.append(bp["lower"])
    uppers.append(bp["upper"])

  bc = ci_results.get("bootstrap_bca", {})
  if bc:
    methods.append("Bootstrap\n(BCa)")
    estimates.append(bc["estimate"])
    lowers.append(bc["lower"])
    uppers.append(bc["upper"])

  x = np.arange(len(methods))
  errors = [[e - l for e, l in zip(estimates, lowers)],
            [u - e for e, u in zip(estimates, uppers)]]

  ax.bar(x, estimates, color="steelblue", alpha=0.7, label="均值估计")
  ax.errorbar(x, estimates, yerr=errors, fmt="none", color="black", capsize=8, label="95% CI")

  ax.set_xticks(x)
  ax.set_xticklabels(methods)
  ax.set_ylabel("误差均值 (km)")
  ax.set_title(f"{orbit} {day}天预报：Gaussian vs Bootstrap 置信区间对比")
  ax.legend()
  ax.grid(True, axis="y", alpha=0.4)
  fig.tight_layout()
  path = out_dir / f"ci_comparison_{orbit}_day{day}.png"
  fig.savefig(path, bbox_inches="tight")
  plt.close(fig)
  return path


def plot_literature_benchmark(summary: pd.DataFrame, out_dir: Path) -> Path:
  """与《空间科学学报》典型量级对标。"""
  fig, ax = plt.subplots(figsize=(9, 5), dpi=120)
  orbits = ["LEO", "MEO", "GEO"]
  days = sorted(summary["Day"].unique())
  x = np.arange(len(days))
  width = 0.25

  for i, orbit in enumerate(orbits):
    ours = []
    lit_mid = []
    for d in days:
      row = summary[(summary["Orbit"] == orbit) & (summary["Day"] == d)]
      ours.append(row["median"].values[0] if len(row) else np.nan)
      lo, hi = LITERATURE_BENCHMARK[orbit][d]
      lit_mid.append((lo + hi) / 2)
    ax.bar(x + i * width, ours, width, label=f"{orbit} 本研究")
    ax.plot(x + i * width, lit_mid, "k_", markersize=12, markeredgewidth=2)

  ax.set_xticks(x + width)
  ax.set_xticklabels([f"{d}天" for d in days])
  ax.set_ylabel("位置误差中位数 (km)")
  ax.set_title("本研究结果 vs 空间科学学报典型量级（黑叉为文献中值）")
  ax.legend()
  ax.grid(True, axis="y", alpha=0.4)
  fig.tight_layout()
  path = out_dir / "literature_benchmark.png"
  fig.savefig(path, bbox_inches="tight")
  plt.close(fig)
  return path


def plot_error_distribution(df: pd.DataFrame, out_dir: Path) -> Path:
  """分轨道、分天数的误差分布箱线图。"""
  fig, axes = plt.subplots(1, 3, figsize=(14, 5), dpi=120, sharey=True)
  days = sorted(df["Day"].unique())

  for ax, day in zip(axes, days):
    sub = df[df["Day"] == day]
    data = [sub[sub["Orbit"] == o]["Error_km"].values for o in ["LEO", "MEO", "GEO"]]
    ax.boxplot(data, labels=["LEO", "MEO", "GEO"])
    ax.set_title(f"预报 {day} 天")
    ax.set_ylabel("误差 (km)" if day == days[0] else "")
    ax.grid(True, axis="y", alpha=0.4)

  fig.suptitle("三轨道类型预报误差分布（箱线图）", fontsize=13, fontweight="bold")
  fig.tight_layout()
  path = out_dir / "error_boxplot.png"
  fig.savefig(path, bbox_inches="tight")
  plt.close(fig)
  return path


def generate_all_plots(
  df: pd.DataFrame,
  summary: pd.DataFrame,
  growth_results: dict,
  ci_by_group: dict,
  out_dir: Path | None = None,
) -> list[Path]:
  """生成全部图表。"""
  out_dir = out_dir or OUTPUT_DIR
  paths = []
  paths.append(plot_error_growth(df, growth_results, out_dir))
  paths.append(plot_error_distribution(df, out_dir))
  paths.append(plot_literature_benchmark(summary, out_dir))
  for (orbit, day), ci in ci_by_group.items():
    paths.append(plot_ci_comparison(ci, orbit, day, out_dir))
  return paths
