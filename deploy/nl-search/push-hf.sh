#!/usr/bin/env bash
# 本地一键推送 nl-search 到 Hugging Face Space（需 HF_TOKEN）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HF_SPACE="${HF_SPACE:-sxyfe/nl-flight-search}"
BUNDLE="$ROOT/.hf-space-bundle"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "请先 export HF_TOKEN=hf_xxx（https://huggingface.co/settings/tokens）"
  exit 1
fi

rm -rf "$BUNDLE"
mkdir -p "$BUNDLE/web" "$BUNDLE/.cursor/skills/flight-monitor-agent"
cp "$ROOT/deploy/nl-search/Dockerfile" "$BUNDLE/Dockerfile"
cp "$ROOT/deploy/nl-search/README.md" "$BUNDLE/README.md"
cp -r "$ROOT/scripts" "$BUNDLE/scripts"
cp -r "$ROOT/web/nl-search" "$BUNDLE/web/nl-search"
cp -r "$ROOT/.cursor/skills/flight-monitor-agent/scripts" "$BUNDLE/.cursor/skills/flight-monitor-agent/scripts"
rm -rf "$BUNDLE/web/nl-search/.venv" "$BUNDLE/web/nl-search/__pycache__" 2>/dev/null || true

python3 - <<PY
from huggingface_hub import HfApi
api = HfApi(token="${HF_TOKEN}")
repo_id = "${HF_SPACE}"
try:
    api.create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
except Exception as e:
    print("create_repo:", e)
api.upload_folder(
    folder_path="${BUNDLE}",
    repo_id=repo_id,
    repo_type="space",
    commit_message="Deploy nl-search",
)
print(f"已上传: https://huggingface.co/spaces/{repo_id}")
PY
