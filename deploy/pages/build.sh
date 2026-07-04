#!/usr/bin/env bash
# 构建 GitHub Pages 静态包：/ 官网，/nl-search/ 查价，/skill/ Skill
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/deploy/pages/dist"

rm -rf "$OUT"
mkdir -p "$OUT/nl-search" "$OUT/skill"

# 官网落地页
cp "$ROOT/web/landing/index.html" "$OUT/index.html"
cp "$ROOT/web/landing/site.css" "$OUT/site.css"
cp "$ROOT/web/landing/skill/index.html" "$OUT/skill/index.html"

# nl-search 静态
cp -R "$ROOT/web/nl-search/static/." "$OUT/nl-search/"

PAGES_PREFIX="${PAGES_PREFIX:-/flight-monitor}"
WEB_BASE="${PAGES_PREFIX}/nl-search"

INDEX="$OUT/nl-search/index.html"
if ! grep -q 'name="web-base"' "$INDEX"; then
  sed -i.bak "s|<head>|<head>\n    <meta name=\"web-base\" content=\"${WEB_BASE}\" />|" "$INDEX"
  rm -f "$INDEX.bak"
fi

if grep -q '<!-- VIZ_NAV -->' "$INDEX"; then
  sed -i.bak 's|<!-- VIZ_NAV -->|<a href="../" class="btn btn-ghost" style="text-decoration:none">首页</a><a href="../skill/" class="btn btn-ghost" style="text-decoration:none">Skill</a>|' "$INDEX"
  rm -f "$INDEX.bak"
fi

echo "Built static site at $OUT (web-base=${WEB_BASE})"
