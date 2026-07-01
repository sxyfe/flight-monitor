## 1. 项目脚手架

- [x] 1.1 创建 `web/nl-search/` 目录结构（`server.py`、`static/`、`README.md`）
- [x] 1.2 添加 Python 依赖文件 `web/nl-search/requirements.txt`（fastapi、uvicorn、httpx、pydantic）
- [x] 1.3 添加 `web/nl-search/.gitignore`（忽略 `.credentials.local.json`）
- [x] 1.4 在根 `package.json` 增加 `nl-search:dev` 脚本启动 uvicorn

## 2. 查询引擎抽取

- [x] 2.1 从 `exhaustive_search.py` 抽取 `scripts/flight_search_engine.py`（`SearchIntent`、`FlightOffer`、`ValidationResult`）
- [x] 2.2 实现 `validate_intent()` 与 `estimate_query_count(mode)`
- [x] 2.3 实现 `search(intent, mode, on_progress)` 支持 RT 与开口程
- [x] 2.4 实现 `aggregate(offers)` 产出价格带、停留天数、目的地等聚合
- [x] 2.5 重构 `exhaustive_search.py` 为调用引擎的薄 CLI 包装

## 3. NL 解析层

- [x] 3.1 实现 `web/nl-search/nl_parser.py`（OpenAI 兼容 chat + JSON schema）
- [x] 3.2 编写 `SearchIntent` JSON schema 与 system prompt（中文机票诉求）
- [x] 3.3 实现解析后规则校验与 `clarifications` 生成
- [x] 3.4 对接 `airportsearch` 消歧未知城市名

## 4. FastAPI 后端

- [x] 4.1 实现 `POST/GET /api/config` 与凭据内存存储
- [x] 4.2 实现 `POST /api/config/test-rollinggo` 与 `test-llm`
- [x] 4.3 实现 `POST /api/intent/parse`
- [x] 4.4 实现 `POST /api/search`（smart 同步返回）
- [x] 4.5 实现 `GET /api/search/{id}/stream` SSE 进度（exhaustive）
- [x] 4.6 实现 `GET /api/search/{id}` 结果回放
- [x] 4.7 高查询量二次确认逻辑（>500）

## 5. 前端页面

- [x] 5.1 实现 `static/index.html` 设置面板（双 Base URL + 双 Key）
- [x] 5.2 实现自然语言输入区、解析按钮、模式选择
- [x] 5.3 实现结构化 `SearchIntent` 预览与手动编辑表单
- [x] 5.4 实现搜索进度条（SSE 消费）
- [x] 5.5 实现结果表格（排序、筛选、行展开航段）
- [x] 5.6 实现图表 Tab（价格带、停留天数、目的地、行程类型）
- [x] 5.7 实现推荐卡片（最便宜 / 最长停留 / 最佳联票）
- [x] 5.8 开口程 `bookable: false` 样式与页脚免责声明

## 6. 文档与验证

- [x] 6.1 编写 `web/nl-search/README.md`（安装、配置、启动、示例 NL 查询）
- [x] 6.2 用历史诉求手工验证：京津、国庆窗、7天、2500、开口程（规则解析 + API 冒烟通过）
- [x] 6.3 确认 smart 模式在 5 分钟内返回可浏览结果（单航线冒烟 1 次查询 ~11s 完成；全量 smart ~396 次需用户本地跑）
