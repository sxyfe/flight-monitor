# 变更：Web 会员订阅与 Stripe 支付

## 背景

方向 A 商业化需在 Web 端提供可售卖的会员套餐，并对接支付与权益门禁。

## 范围

- 新增 `web/billing`：注册/登录、六档套餐、Stripe Checkout + Webhook、Mock 支付
- `web/shared/subscription_gate.py` 供 nl-search / flight-watch 权益检查
- 网关挂载 `/billing/`；落地页与顶栏导航增加订阅入口

## 套餐

| 套餐 | 时长 | 日搜索 | 监控条数 | 穷举 |
|------|------|--------|----------|------|
| 免费试用 | 7 天 | 30 | 1 | 否 |
| 一周 | 7 天 | 200 | 3 | 是 |
| 两周 | 14 天 | 400 | 5 | 是 |
| 月度 | 30 天订阅 | 800 | 10 | 是 |
| 年度 | 365 天订阅 | 2000 | 30 | 是 |
| 永久 | 永久 | 5000 | 50 | 是 |

## 环境变量

- `BILLING_ENABLED`（默认 true）
- `BILLING_JWT_SECRET`、`BILLING_DB_PATH`
- `STRIPE_SECRET_KEY`、`STRIPE_WEBHOOK_SECRET`、`PUBLIC_BASE_URL`
- `BILLING_MOCK_PAY`（auto/true/false）

## 非目标

- 平台代付 RollingGo Key（用户仍自备 Key）
- 多租户 PostgreSQL（当前 SQLite，可后续迁移）
