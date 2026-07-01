## 1. OpenSpec 产物

- [x] 1.1 创建 change `flight-monitor-agent-oss`
- [x] 1.2 撰写 proposal.md、design.md、specs、tasks.md

## 2. 配置与引擎解耦

- [x] 2.1 新增 `scripts/config.py`、`.env.example`、`.gitignore`
- [x] 2.2 vendored `flight_search_engine.py` 至 Skill scripts/
- [x] 2.3 删除 `_project.py`；更新脚本 import
- [x] 2.4 新增 `scripts/check_rollinggo.py`

## 3. 查价 CLI

- [x] 3.1 `run_search.py`：`--mode`、`--confirm`、耗时估算
- [x] 3.2 `parse_nl_intent.py` 使用 config 加载 Key

## 4. 报告与文档

- [x] 4.1 `generate_flight_report.py` 移除 monitor 逻辑
- [x] 4.2 重写 `SKILL.md`（纯查价、rollinggo.store、反滥用）
- [x] 4.3 新建 `README.md`（中英双语）
- [x] 4.4 `templates/mcp.json.example`

## 5. 独立仓库

- [x] 5.1 添加 `LICENSE`、`STANDALONE_REPO.md` 发布说明
- [x] 5.2 更新 monorepo README / AGENTS.md 链接
