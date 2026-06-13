# TLE 预报精度统计分析

基于 **Space-Track** 历史 TLE 与 **SGP4** 传播器，对 LEO / MEO / GEO 三类轨道卫星进行位置预报精度统计分析。


## 快速开始

```bash
git clone https://github.com/xingweitong1/tle-forecast-analysis.git
cd tle-forecast-analysis
pip install -r requirements.txt
python main.py
```

无需 Space-Track 账号即可复现分析（使用仓库内 TLE 缓存）。

## 统计方法链

```
差分法预报误差 → 协方差传播 Σ(Δt)=ΦΣ₀Φᵀ+Q → 增长律拟合
  → Bootstrap 置信区间（Percentile / BCa）→ Gaussian 对比
  → Kruskal-Wallis 轨道类型差异检验
```

## 项目结构

```
├── main.py                     # 主入口
├── config.py                   # 卫星 NORAD ID、参数
├── requirements.txt
├── data/
│   ├── raw/spacetrack/         # 已下载 TLE
│   └── processed/              # 运行后生成的数据
├── output/                     # 图表与报告
└── src/
    ├── download/               # Space-Track 下载 / 本地缓存
    ├── propagation/            # SGP4 差分法
    ├── statistics/             # Bootstrap、协方差、检验
    └── visualization/          # 绘图
```

## 更新 TLE 数据（可选）

```bash
export SPACETRACK_USER=你的用户名
export SPACETRACK_PASSWORD=你的密码
python main.py --download
```

Windows PowerShell:

```powershell
$env:SPACETRACK_USER = "你的用户名"
$env:SPACETRACK_PASSWORD = "你的密码"
python main.py --download
```

## 输出文件

| 路径 | 说明 |
|------|------|
| `data/processed/errors_all.csv` | 全部差分误差 |
| `data/processed/summary_by_orbit_day.csv` | 汇总统计 |
| `output/report.json` | 结构化报告 |
| `output/*.png` | 图表 |


