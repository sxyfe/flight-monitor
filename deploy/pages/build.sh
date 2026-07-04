#!/usr/bin/env bash
# 构建 GitHub Pages 静态包：/ 官网，/viz/ 雷达，/nl-search/ 查价，/skill/ Cursor Skill
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/deploy/pages/dist"

rm -rf "$OUT"
mkdir -p "$OUT/viz" "$OUT/nl-search" "$OUT/skill"

# 官网落地页
cp "$ROOT/web/landing/index.html" "$OUT/index.html"
cp "$ROOT/web/landing/site.css" "$OUT/site.css"
cp "$ROOT/web/landing/skill/index.html" "$OUT/skill/index.html"

# exhaustive-viz → /viz/
cp -R "$ROOT/web/exhaustive-viz/." "$OUT/viz/"
if [ -L "$OUT/viz/data.json" ]; then
  target="$(readlink -f "$ROOT/web/exhaustive-viz/data.json")"
  rm "$OUT/viz/data.json"
  if [ -f "$target" ]; then
    cp "$target" "$OUT/viz/data.json"
  else
    printf '%s\n' '{"rt_hits":[],"oj_hits":[],"destinations_by_country":{},"meta":{}}' > "$OUT/viz/data.json"
  fi
fi

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
  sed -i.bak 's|<!-- VIZ_NAV -->|<a href="../" class="btn btn-ghost" style="text-decoration:none">首页</a><a href="../skill/" class="btn btn-ghost" style="text-decoration:none">Cursor Skill</a>|' "$INDEX"
  rm -f "$INDEX.bak"
fi

echo "Built static site at $OUT (web-base=${WEB_BASE})"
