# 上传 GitHub 指南

本文件夹 `tle_forecast_github/` 是可直接上传 GitHub 的独立版本：

- **已包含** `data/raw/spacetrack/` 下 15 颗卫星的 TLE 原始数据
- **未包含** `output/` 和 `data/processed/` 中的分析结果
- **未包含** Space-Track 账号密码（请用环境变量，不要写进代码）

---

## 方式一：GitHub 网页上传（最简单）

1. 登录 [GitHub](https://github.com)，点击右上角 **+** → **New repository**
2. 填写仓库名，例如 `tle-forecast-analysis`
3. 选择 **Public** 或 **Private**，**不要**勾选 “Add a README”（本仓库已有）
4. 点击 **Create repository**
5. 在新仓库页面点击 **uploading an existing file**
6. 将 `tle_forecast_github` 文件夹内的**全部文件和子文件夹**拖入浏览器
7. 底部填写提交说明，例如 `Initial commit: code + Space-Track TLE cache`
8. 点击 **Commit changes**

> 注意：若 TLE 文件较多导致网页上传失败，请用下面的 Git 命令行方式。

---

## 方式二：Git 命令行（推荐）

在 PowerShell 中执行（路径按你的实际位置修改）：

```powershell
cd "c:\Users\xj045\Desktop\数理统计作业\tle_forecast_github"

# 初始化 Git 仓库
git init

# 添加所有文件（.gitignore 会自动排除 output/ 和 processed/ 中的结果）
git add .

# 查看将要提交的内容（确认没有 .env 或密码）
git status

# 首次提交
git commit -m "Initial commit: TLE forecast analysis with Space-Track data cache"

# 关联远程仓库（替换为你的 GitHub 用户名和仓库名）
git remote add origin https://github.com/你的用户名/tle-forecast-analysis.git

# 推送到 GitHub（主分支名为 main）
git branch -M main
git push -u origin main
```

首次 `git push` 时，GitHub 会弹出浏览器要求登录授权。

---

## 方式三：GitHub Desktop

1. 下载安装 [GitHub Desktop](https://desktop.github.com/)
2. **File → Add local repository**，选择 `tle_forecast_github` 文件夹
3. 若提示不是 Git 仓库，点击 **create a repository**
4. 填写 Summary，点击 **Commit to main**
5. **Publish repository** 发布到 GitHub

---

## 上传前检查清单

| 检查项 | 说明 |
|--------|------|
| ☐ 无 `.env` 文件 | 只有 `.env.example`，不含真实密码 |
| ☐ 无 `output/*.png` | 结果目录应为空（仅 `.gitkeep`） |
| ☐ 无 `data/processed/*.csv` | 处理结果不应提交 |
| ☐ 有 15 个 `.tle` 文件 | 在 `data/raw/spacetrack/` 下 |
| ☐ 无 `__pycache__/` | 已被 `.gitignore` 排除 |

运行以下命令快速确认：

```powershell
cd "c:\Users\xj045\Desktop\数理统计作业\tle_forecast_github"
git status
# 或尚未 init 时：
Get-ChildItem output, data\processed -Recurse
Get-ChildItem data\raw\spacetrack\*.tle | Measure-Object
```

应看到：TLE 文件 15 个；`output/` 和 `data/processed/` 只有 `.gitkeep`。

---

## 克隆后如何使用

其他人克隆你的仓库后：

```bash
git clone https://github.com/你的用户名/tle-forecast-analysis.git
cd tle-forecast-analysis
pip install -r requirements.txt
python main.py
```

程序自动读取仓库内的 TLE 缓存，生成 `output/` 和 `data/processed/` 中的结果。

---

## 常见问题

**Q: push 时要求输入用户名密码？**  
A: GitHub 已不支持密码推送，需使用 [Personal Access Token](https://github.com/settings/tokens) 作为密码，或配置 SSH 密钥。

**Q: 文件太大 push 失败？**  
A: 15 个 TLE 文件通常几 MB，一般没问题。若超限，检查是否误提交了 `output/` 中的 PNG。

**Q: 想更新 TLE 后再 push？**  
A: 设置 Space-Track 凭证后运行 `python main.py --download`，然后 `git add data/raw/spacetrack/` 并 commit。
