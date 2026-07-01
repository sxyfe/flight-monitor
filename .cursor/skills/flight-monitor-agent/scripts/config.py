"""Skill 根目录、配置与 RollingGo Key 加载。"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SKILL_ROOT / "output"
DEFAULT_BASE_URL = "https://mcp.rollinggo.cn"
KEY_APPLY_URL = "https://rollinggo.store/"
AVG_LATENCY_SEC = 1.0


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _token_from_mcp_json() -> str | None:
    mcp = Path.home() / ".cursor/mcp.json"
    if not mcp.exists():
        return None
    try:
        data = json.loads(mcp.read_text(encoding="utf-8"))
        auth = data["mcpServers"]["RollingGo-Flight"]["headers"]["Authorization"]
        return auth.split(" ", 1)[1]
    except (KeyError, IndexError, json.JSONDecodeError):
        return None


def load_settings() -> Settings:
    """优先级：环境变量 > .env > ~/.cursor/mcp.json。"""
    _load_dotenv(SKILL_ROOT / ".env")
    api_key = os.environ.get("ROLLINGGO_API_KEY") or _token_from_mcp_json() or ""
    base_url = (os.environ.get("ROLLINGGO_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    return Settings(api_key=api_key, base_url=base_url)


def missing_key_message() -> str:
    return (
        "未配置 RollingGo API Key。\n"
        f"1. 在 {KEY_APPLY_URL} 申请 Key（格式 mcp_...）\n"
        f"2. 复制 .env.example 为 .env 并填入 ROLLINGGO_API_KEY\n"
        "   或 export ROLLINGGO_API_KEY=mcp_...\n"
        "3. 运行: python3 scripts/check_rollinggo.py"
    )


def ensure_api_key() -> Settings:
    settings = load_settings()
    if not settings.api_key:
        print(missing_key_message(), file=sys.stderr)
        sys.exit(1)
    return settings


def setup_scripts_path() -> None:
    """确保 scripts/ 在 sys.path 首位（独立仓库内 import）。"""
    p = str(SCRIPTS_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)
