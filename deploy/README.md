# Web 统一部署

`web/` 下两个工具通过 **统一网关** 发布到 **同一域名**：

| 路径 | 功能 |
|------|------|
| `/` | Flight Monitor 官网落地页 |
| `/nl-search/` | 自然语言查价（nl-search，含 API / SSE） |
| `/billing/` | 使用说明（查价/监控免费，无需注册） |
| `/skill/` | Cursor Skill（flight-monitor-agent）介绍与安装 |

> **说明**：GitHub Pages **只能托管静态文件**，无法在 `github.io` 上运行查价 API。  
> 若要 **完整功能 + 同一域名**，请使用下方 **Render / Docker** 方案。  
> GitHub Pages 仍会发布静态镜像（查价页 UI 可打开，但搜索 API 不可用）。

---

## 方案一：Render（推荐，免费档）

1. 打开 [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
2. 连接 GitHub 仓库 `sxyfe/flight-monitor`，使用根目录 `render.yaml`
3. 在服务 **Environment** 中添加：
   - `ROLLINGGO_API_KEY`（必填，[rollinggo.store](https://rollinggo.store/) 申请）
   - `LLM_API_KEY`（可选）
   - `LLM_BASE_URL`、`LLM_MODEL`（可选）
4. 部署完成后访问 Render 提供的 URL，例如 `https://flight-monitor-web.onrender.com`
5. （可选）在 Render 服务 **Settings → Deploy Hook** 复制 URL，写入 GitHub Secrets：`RENDER_DEPLOY_HOOK`，推送 `main` 后自动重建

**本地 Docker 预览：**

```bash
docker build -f deploy/web/Dockerfile -t flight-monitor-web .
docker run -p 7860:7860 -e ROLLINGGO_API_KEY=你的Key flight-monitor-web
# 查价     http://127.0.0.1:7860/nl-search/
# 说明     http://127.0.0.1:7860/billing/
# 官网     http://127.0.0.1:7860/
# Skill    http://127.0.0.1:7860/skill/
```

---

## 方案二：GitHub Pages（仅静态）

1. 仓库 **Settings → Pages**：Source 选 `gh-pages` 分支 / `(root)`
2. 推送 `main` 后 workflow `Deploy web to GitHub Pages` 自动构建并发布
3. 访问：https://sxyfe.github.io/flight-monitor/
   - `/` — 官网
   - `/nl-search/` — 查价 UI（**无后端，无法实际搜索**）

---

## 本地开发

```bash
# 统一网关（推荐，与线上一致：/、/nl-search/、/billing/、/flight-watch/、/skill/）
npm run nl-search:dev

# 等价命令
PYTHONPATH=. WEB_ROOT=/nl-search python -m uvicorn web.gateway.server:app --reload --port 8765

# 仅 nl-search 子应用（无 billing 等子路径）
cd web/nl-search && python3 -m uvicorn server:app --host 127.0.0.1 --port 8765
```

---

## 目录

```
web/gateway/server.py      # 统一 FastAPI 网关
deploy/web/Dockerfile      # 生产镜像
deploy/pages/build.sh      # GitHub Pages 静态构建
render.yaml                # Render Blueprint
```
