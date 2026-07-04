#!/usr/bin/env python3
"""本地验证 Web 网关可加载（非部署）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_gateway():
    spec = importlib.util.spec_from_file_location(
        "gateway_server", ROOT / "web" / "gateway" / "server.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 gateway server")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.app


def main() -> int:
    try:
        from fastapi import FastAPI  # noqa: F401
    except ImportError:
        print("SKIP: fastapi 未安装，跳过网关导入验证")
        return 0

    app = _load_gateway()
    paths = {getattr(r, "path", "") for r in app.routes}
    required = {"/nl-search", "/flight-watch", "/viz", "/skill"}
    missing = required - paths
    if missing:
        print("FAIL: 缺少挂载路径", missing)
        return 1
    print("OK: gateway 路由", sorted(p for p in paths if p in required | {"/"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
