"""项目配置：卫星分组、预报时长、数据源参数。"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"

for d in (RAW_DIR, PROCESSED_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)

# 预报时长（天）
FORECAST_DAYS = [1, 3, 7]
# 预报时长容差（天）：配对 TLE 历元差允许偏差
FORECAST_TOLERANCE_DAYS = 0.5

# 数据回溯窗口
LOOKBACK_DAYS = 90

# 三组轨道类型及代表性 NORAD ID（每组多个卫星）
ORBIT_SATELLITES = {
    "LEO": [
        25544,   # ISS
        20580,   # Hubble
        43013,   # Starlink
        48274,   # CSS Tianhe
        33591,   # NOAA-19
    ],
    "MEO": [
        37753,   # GPS IIF-1
        28915,   # GLONASS
        37846,   # Galileo
        40105,   # BeiDou-3
        43001,   # GPS III
    ],
    "GEO": [
        41866,   # GOES-16
        41882,   # Fengyun-4A
        39070,   # INMARSAT
        40367,   # SBIRS GEO-1
        28884,   # INTELSAT 11
    ],
}

# Space-Track 凭证（环境变量优先）
import os

SPACETRACK_USER = os.environ.get("SPACETRACK_USER", "")
SPACETRACK_PASSWORD = os.environ.get("SPACETRACK_PASSWORD", "")

# Bootstrap 参数
BOOTSTRAP_N = 5000
CONFIDENCE_LEVEL = 0.95

# 对标文献参考值（中科院空间中心《空间科学学报》量级，单位 km）
# 来源：TLE 预报精度典型研究，用于结果对比讨论
LITERATURE_BENCHMARK = {
    "LEO": {1: (1.0, 3.0), 3: (3.0, 8.0), 7: (8.0, 20.0)},
    "MEO": {1: (0.5, 1.5), 3: (1.0, 3.0), 7: (2.0, 5.0)},
    "GEO": {1: (0.5, 2.0), 3: (1.0, 3.5), 7: (1.5, 5.0)},
}


def date_range_utc():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=LOOKBACK_DAYS)
    return start, end
