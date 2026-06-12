"""Space-Track.org 历史 TLE 下载（需免费注册账号）。"""

import time
from datetime import datetime
from pathlib import Path

import requests

from config import RAW_DIR, SPACETRACK_PASSWORD, SPACETRACK_USER

LOGIN_URL = "https://www.space-track.org/ajaxauth/login"
QUERY_BASE = "https://www.space-track.org/basicspacedata/query"


class SpaceTrackClient:
  """Space-Track REST API 客户端。"""

  def __init__(self, identity: str, password: str):
    self.session = requests.Session()
    self.identity = identity
    self.password = password
    self._logged_in = False

  def login(self) -> bool:
    resp = self.session.post(
      LOGIN_URL,
      data={"identity": self.identity, "password": self.password},
      timeout=30,
    )
    self._logged_in = resp.status_code == 200
    return self._logged_in

  def query_gp_history(
    self,
    norad_id: int,
    start: datetime,
    end: datetime,
  ) -> str:
    """下载指定 NORAD ID 在 [start, end] 内的全部 GP 历史 TLE。"""
    if not self._logged_in and not self.login():
      raise ConnectionError("Space-Track 登录失败，请检查 SPACETRACK_USER/PASSWORD")

    start_s = start.strftime("%Y-%m-%d")
    end_s = end.strftime("%Y-%m-%d")
    url = (
      f"{QUERY_BASE}/class/gp_history/"
      f"NORAD_CAT_ID/{norad_id}/"
      f"EPOCH/{start_s}--{end_s}/"
      f"orderby/EPOCH%20asc/format/tle"
    )
    resp = self.session.get(url, timeout=120)
    resp.raise_for_status()
    return resp.text.strip()

  def query_gp_recent(self, norad_id: int, days: int = 90) -> str:
    """使用 gp 类查询最近 N 天 TLE（备选接口）。"""
    if not self._logged_in and not self.login():
      raise ConnectionError("Space-Track 登录失败")

    url = (
      f"{QUERY_BASE}/class/gp/"
      f"NORAD_CAT_ID/{norad_id}/"
      f"EPOCH/>now-{days}/"
      f"orderby/EPOCH%20asc/format/tle"
    )
    resp = self.session.get(url, timeout=120)
    resp.raise_for_status()
    return resp.text.strip()


def download_spacetrack_history(
  norad_id: int,
  start: datetime,
  end: datetime,
  save_dir: Path | None = None,
  client: SpaceTrackClient | None = None,
) -> Path | None:
  """循环下载单颗卫星历史 TLE 并保存。"""
  save_dir = save_dir or RAW_DIR / "spacetrack"
  save_dir.mkdir(parents=True, exist_ok=True)
  out_path = save_dir / f"{norad_id}_{start:%Y%m%d}_{end:%Y%m%d}.tle"

  if out_path.exists() and out_path.stat().st_size > 0:
    return out_path

  user = SPACETRACK_USER
  password = SPACETRACK_PASSWORD
  if not user or not password:
    return None

  client = client or SpaceTrackClient(user, password)
  try:
    text = client.query_gp_history(norad_id, start, end)
    if not text:
      text = client.query_gp_recent(norad_id, days=(end - start).days)
    if not text:
      return None
    out_path.write_text(text + "\n", encoding="utf-8")
    return out_path
  except requests.RequestException:
    return None


def load_cached_spacetrack_paths(
  orbit_satellites: dict[str, list[int]],
  save_dir: Path | None = None,
) -> dict[str, dict[int, Path]]:
  """从本地 data/raw/spacetrack/ 加载已下载的 TLE 文件（无需网络）。"""
  save_dir = save_dir or RAW_DIR / "spacetrack"
  if not save_dir.exists():
    return {}

  results: dict[str, dict[int, Path]] = {}
  for orbit, ids in orbit_satellites.items():
    results[orbit] = {}
    for nid in ids:
      matches = sorted(save_dir.glob(f"{nid}_*.tle"))
      if matches and matches[0].stat().st_size > 0:
        results[orbit][nid] = matches[0]
  return results


def download_all_satellites(
  orbit_satellites: dict[str, list[int]],
  start: datetime,
  end: datetime,
  delay: float = 1.0,
) -> dict[str, dict[int, Path]]:
  """按轨道类型循环下载全部卫星 TLE。"""
  if not SPACETRACK_USER or not SPACETRACK_PASSWORD:
    return {}

  client = SpaceTrackClient(SPACETRACK_USER, SPACETRACK_PASSWORD)
  if not client.login():
    return {}

  results: dict[str, dict[int, Path]] = {}
  for orbit, ids in orbit_satellites.items():
    results[orbit] = {}
    for nid in ids:
      path = download_spacetrack_history(nid, start, end, client=client)
      if path:
        results[orbit][nid] = path
      time.sleep(delay)
  return results
