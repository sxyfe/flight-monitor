#!/usr/bin/env bash
# 构建 GitHub Pages 静态包：/ 穷举可视化，/nl-search/ 查价前端（无 API，完整功能需 Render 网关）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/deploy/pages/dist"

rm -rf "$OUT"
mkdir -p "$OUT/nl-search"

# exhaustive-viz → 站点根目录
cp -R "$ROOT/web/exhaustive-viz/." "$OUT/"
if [ -L "$OUT/data.json" ]; then
  target="$(readlink -f "$ROOT/web/exhaustive-viz/data.json")"
  rm "$OUT/data.json"
  cp "$target" "$OUT/data.json"
fi

# nl-search 静态资源（子路径 nl-search/）
cp -R "$ROOT/web/nl-search/static/." "$OUT/nl-search/"

PAGES_PREFIX="${PAGES_PREFIX:-/flight-monitor}"
WEB_BASE="${PAGES_PREFIX}/nl-search"

# 注入 web-base（GitHub Pages 项目站需 /flight-monitor/nl-search 前缀）
INDEX="$OUT/nl-search/index.html"
if ! grep -q 'name="web-base"' "$INDEX"; then
  sed -i.bak "s|<head>|<head>\n    <meta name=\"web-base\" content=\"${WEB_BASE}\" />|" "$INDEX"
  rm -f "$INDEX.bak"
fi

# 静态镜像下显示返回穷举雷达的链接
if grep -q '<!-- VIZ_NAV -->' "$INDEX"; then
  sed -i.bak 's|<!-- VIZ_NAV -->|<a href="../" class="btn btn-ghost" style="text-decoration:none">穷举雷达</a>|' "$INDEX"
  rm -f "$INDEX.bak"
fi

echo "Built static site at $OUT (web-base=${WEB_BASE})"
