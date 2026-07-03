#!/usr/bin/env bash
# 通过 Render API 创建 Blueprint 部署（需先 export RENDER_API_KEY=...）
# 文档：https://render.com/docs/api
set -euo pipefail

if [[ -z "${RENDER_API_KEY:-}" ]]; then
  echo "请设置 RENDER_API_KEY（Render Dashboard → Account Settings → API Keys）" >&2
  exit 1
fi

REPO="${REPO:-https://github.com/sxyfe/flight-monitor}"
BRANCH="${BRANCH:-main}"
NAME="${NAME:-flight-monitor-web}"

echo "创建 Blueprint: ${NAME} (${REPO}@${BRANCH})"

RESP=$(curl -fsS -X POST "https://api.render.com/v1/blueprints" \
  -H "Authorization: Bearer ${RENDER_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"${NAME}\",
    \"repo\": \"${REPO}\",
    \"branch\": \"${BRANCH}\",
    \"autoSync\": true
  }")

echo "$RESP" | python3 -m json.tool 2>/dev/null || echo "$RESP"
echo ""
echo "下一步：在 Render Dashboard 为该服务设置 ROLLINGGO_API_KEY 环境变量。"
