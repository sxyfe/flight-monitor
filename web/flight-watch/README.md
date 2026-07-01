# Flight Watch

独立 Web 机票监控工具：创建全球任意 OD 的 Watch 规则，定时查价，命中限价或降价时通过 **飞书 + PushPlus** 通知。与 Tauri 桌面监控、nl-search 查价 **无数据打通**。

默认地址：<http://127.0.0.1:8767>

## 前置条件

- Python 3.10+
- RollingGo Flight API Key（[rollinggo.store](https://rollinggo.store/)）
- 可选：飞书 Webhook、PushPlus token
- 可选：`swoop-flights` 用于多段/开口 **同票** 查价（已写入 requirements）

## 安装与启动

```bash
cd web/flight-watch
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 或项目根目录
npm run flight-watch:dev
```

## 配置

1. 打开设置页，填写 RollingGo Key、飞书 Webhook、PushPlus token
2. 点击测试按钮验证连通性
3. 凭据保存在 `web/flight-watch/.credentials.local.json`（已 gitignore）

## 使用

- **新建监控**：选择行程类型（往返/单程/多段/开口），填写航段与限价
- **全球机场**：输入中文城市名或 IATA，调用 RollingGo airportsearch
- **预设库**：一键导入 15 条达美开口示例（默认未启用）
- **立即查价**：列表页手动触发；历史页查看快照

## 定时监控

**方式 A（推荐）**：保持 `npm run flight-watch:dev` 进程运行，内置 APScheduler 按 `interval_hours` 轮询。

**方式 B**：本机 cron 调用 API（服务可不常驻，但需临时启动或仅手动 run-once）：

```bash
0 8,20 * * * curl -s -X POST http://127.0.0.1:8767/api/watch/run-once -H 'Content-Type: application/json' -d '{}'
```

## Spike

```bash
.venv/bin/python spike_swoop.py
```

## 说明

- 多段/开口优先 swoop 同票价；失败时 RollingGo 分段单程相加，`bookable=false`
- 告警逻辑：限价命中、降价优先、24h 冷却（对齐桌面端）
- 连续 3 次查价失败自动暂停并通知
