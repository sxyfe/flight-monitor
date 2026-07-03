---
title: NL Flight Search
emoji: ✈️
colorFrom: orange
colorTo: red
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# NL Flight Search

自然语言 / 表单特价机票查价 Demo（RollingGo 实时查价）。

## 配置（Space Secrets）

在 Space **Settings → Repository secrets** 中添加：

| 变量 | 说明 |
|------|------|
| `ROLLINGGO_API_KEY` | [rollinggo.store](https://rollinggo.store/) 申请的 Key |
| `LLM_API_KEY` | 可选，OpenAI 兼容 LLM Key |
| `LLM_BASE_URL` | 可选，默认 `https://api.openai.com/v1` |
| `LLM_MODEL` | 可选，默认 `gpt-4o-mini` |

未配置 Key 时可在页面「设置」中填写（保存在浏览器会话，重启 Space 后需重填）。
