"""
SGP4 差分法预报误差计算。

方法：以较早 TLE 传播至较晚 TLE 历元时刻的位置为预报值，
以较晚 TLE 在同一时刻的位置为参考真值，二者欧氏距离即为位置误差。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sgp4.api import Satrec, jday

from config import FORECAST_DAYS, FORECAST_TOLERANCE_DAYS


@dataclass
class TLERecord:
  norad_id: int
  line1: str
  line2: str
  epoch: datetime
  satrec: Satrec

  @property
  def epoch_jd(self) -> tuple[float, float]:
    return self.satrec.jdsatepoch, self.satrec.jdsatepochF


def _epoch_from_satrec(sat: Satrec) -> datetime:
  jd = sat.jdsatepoch + sat.jdsatepochF
  # JD to datetime (UTC)
  a = int(jd + 0.5)
  frac = jd + 0.5 - a
  if a < 2299161:
    b = 0
  else:
    alpha = int((a - 1867216.25) / 36524.25)
    b = 1 + alpha - int(alpha / 4)
  c = a + b + 1524
  d = int((c - 122.1) / 365.25)
  e = int(365.25 * d)
  g = int((c - e) / 30.6001)
  day = c - e - int(30.6001 * g) + frac
  month = g - 1 if g < 14 else g - 13
  year = d - 4715 if month > 2 else d - 4716
  hours = (day - int(day)) * 24
  h = int(hours)
  minutes = (hours - h) * 60
  m = int(minutes)
  s = (minutes - m) * 60
  return datetime(year, month, int(day), h, m, int(s), tzinfo=timezone.utc)


def parse_tle_text(text: str) -> list[TLERecord]:
  """解析 TLE 文本（支持带名称行）。"""
  lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
  records: list[TLERecord] = []
  i = 0
  while i < len(lines):
    if lines[i].startswith("1 ") and i + 1 < len(lines) and lines[i + 1].startswith("2 "):
      l1, l2 = lines[i], lines[i + 1]
      i += 2
    elif i + 2 < len(lines) and lines[i + 1].startswith("1 ") and lines[i + 2].startswith("2 "):
      l1, l2 = lines[i + 1], lines[i + 2]
      i += 3
    else:
      i += 1
      continue
    try:
      sat = Satrec.twoline2rv(l1, l2)
      norad = int(l1[2:7])
      epoch = _epoch_from_satrec(sat)
      records.append(TLERecord(norad, l1, l2, epoch, sat))
    except (ValueError, IndexError):
      continue
  records.sort(key=lambda r: r.epoch)
  return records


def parse_tle_file(path: Path) -> list[TLERecord]:
  return parse_tle_text(path.read_text(encoding="utf-8", errors="ignore"))


def calculate_prediction_error(
  tle_past_l1: str,
  tle_past_l2: str,
  tle_ref_l1: str,
  tle_ref_l2: str,
  target_jd: float,
  target_fr: float,
) -> float:
  """
  差分法：用 past TLE 预报，用 ref TLE 作参考。
  在 target_jd + target_fr 时刻计算三维位置误差 (km)。
  """
  sat_past = Satrec.twoline2rv(tle_past_l1, tle_past_l2)
  sat_ref = Satrec.twoline2rv(tle_ref_l1, tle_ref_l2)

  e_past, r_pred, _ = sat_past.sgp4(target_jd, target_fr)
  e_ref, r_ref, _ = sat_ref.sgp4(target_jd, target_fr)

  if e_past != 0 or e_ref != 0:
    return np.nan

  return float(np.linalg.norm(np.array(r_pred) - np.array(r_ref)))


def _find_pairs(
  records: list[TLERecord],
  forecast_days: list[int],
  tolerance_days: float,
) -> list[tuple[TLERecord, TLERecord, int]]:
  """为每颗卫星按预报时长配对 TLE。"""
  pairs: list[tuple[TLERecord, TLERecord, int]] = []
  used = set()

  for d in forecast_days:
    target_delta = d * 86400.0  # seconds
    tol = tolerance_days * 86400.0

    for i, r0 in enumerate(records):
      for j in range(i + 1, len(records)):
        r1 = records[j]
        delta = (r1.epoch - r0.epoch).total_seconds()
        if abs(delta - target_delta) <= tol:
          key = (r0.epoch.isoformat(), r1.epoch.isoformat(), d)
          if key not in used:
            pairs.append((r0, r1, d))
            used.add(key)
  return pairs


def compute_differential_errors(
  records: list[TLERecord],
  orbit_type: str,
  norad_id: int,
  forecast_days: list[int] | None = None,
  tolerance_days: float | None = None,
) -> pd.DataFrame:
  """
  对单颗卫星的全部 TLE 记录执行差分法误差计算。
  返回列：Orbit, NORAD_ID, Day, Error_km, Epoch_past, Epoch_ref, Delta_hours
  """
  forecast_days = forecast_days or FORECAST_DAYS
  tolerance_days = tolerance_days or FORECAST_TOLERANCE_DAYS

  pairs = _find_pairs(records, forecast_days, tolerance_days)
  rows = []

  for r0, r1, d in pairs:
    jd, fr = r1.epoch_jd
    err = calculate_prediction_error(r0.line1, r0.line2, r1.line1, r1.line2, jd, fr)
    if np.isnan(err):
      continue
    delta_h = (r1.epoch - r0.epoch).total_seconds() / 3600.0
    rows.append({
      "Orbit": orbit_type,
      "NORAD_ID": norad_id,
      "Day": d,
      "Error_km": err,
      "Epoch_past": r0.epoch,
      "Epoch_ref": r1.epoch,
      "Delta_hours": delta_h,
    })

  return pd.DataFrame(rows)


def build_error_dataset(
  tle_paths: dict[str, dict[int, Path]],
) -> pd.DataFrame:
  """从已下载 TLE 文件构建完整误差数据集。"""
  frames = []
  for orbit, sat_paths in tle_paths.items():
    for nid, path in sat_paths.items():
      records = parse_tle_file(path)
      if len(records) < 2:
        continue
      df = compute_differential_errors(records, orbit, nid)
      if not df.empty:
        frames.append(df)
  if not frames:
    return pd.DataFrame()
  return pd.concat(frames, ignore_index=True)
