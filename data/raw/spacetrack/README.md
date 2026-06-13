# Space-Track 历史 TLE 缓存

本目录包含已从 Space-Track.org 下载的 GP 历史 TLE 数据。

| 项目 | 内容 |
|------|------|
| 时间范围 | 2026-03-13 ~ 2026-06-11（90 天） |
| 卫星数量 | 15 颗（LEO/MEO/GEO 各 5 颗） |
| 文件格式 | NORAD_ID_起始日期_结束日期.tle |
| 数据来源 | Space-Track `gp_history` API |

克隆仓库后可直接运行 `python main.py`，程序将自动读取本目录缓存，**无需 Space-Track 账号**。

如需更新数据，设置环境变量后运行：

```bash
python main.py --download
```
