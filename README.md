# Flight Monitor

Mac / Windows 桌面客户端：本地 hourly 监控机票含税总价，命中或降价时通过飞书 Webhook 通知（含航班号与时间，无购买链接）。

## 开发环境

- Node.js 20+
- Rust stable（[rustup](https://rustup.rs/)）

## 本地运行

```bash
npm install
npm run tauri:dev
```

若提示找不到 `cargo`，请先安装 Rust 并加载环境：

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
```

也可在 `~/.zshrc` 中加入 `source "$HOME/.cargo/env"`，避免每次手动加载。

## 构建

```bash
npm run tauri:build
```

## 首次使用

1. 在 [rollinggo.store](https://rollinggo.store/) 申请 RollingGo API Key  
2. 在飞书群创建自定义机器人，复制 Webhook  
3. 按应用内向导完成配置并创建唯一监控规则  
4. 保持电脑开机且应用运行（可启用开机自启）

## 已实现能力

- Tauri 2 + Vue 3 桌面壳、系统托盘、关闭窗口隐藏到托盘
- 本机 SQLite 规则/历史、Keychain 凭据存储
- RollingGo 分段查价（开口程为分段最低价相加）
- hourly 轮询 + 手动立即查价
- 降价优先通知 + 24h  unchanged-price 冷却
- 中/英双语 + Light/Dark/System/Claude 四套主题
- Onboarding / 监控面板 / 历史 / 设置

## Agent Skill（独立开源）

纯查价 Skill **[flight-monitor-agent](.cursor/skills/flight-monitor-agent/)** 可独立发布，详见其 [README](.cursor/skills/flight-monitor-agent/README.md) 与 [STANDALONE_REPO.md](.cursor/skills/flight-monitor-agent/STANDALONE_REPO.md)。Key 申请统一入口：[rollinggo.store](https://rollinggo.store/)。

## 说明

- 每位用户仅 1 条监控，最多 5 个城市节点  
- 监控仅在应用运行且电脑开机时生效  
- API Key 与 Webhook 仅存本机，不上传自有服务器
