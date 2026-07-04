"""网关 mount 场景：子应用 lifespan 不运行时仍可导入预设。"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parents[1]
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "scripts"))


def _load_subapp(module_name: str, app_dir: Path):
    app_dir_str = str(app_dir)
    if app_dir_str not in sys.path:
        sys.path.append(app_dir_str)
    spec = importlib.util.spec_from_file_location(module_name, app_dir / "server.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_mounted_preset_import_without_lifespan():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    fw = _load_subapp("flight_watch_server_test", WEB / "flight-watch")
    db = Path(tempfile.mkdtemp()) / "mounted.db"
    fw.store.DB_PATH = db
    fw.store._db_initialized = False

    gateway = FastAPI()
    gateway.mount("/flight-watch", fw.app)
    client = TestClient(gateway)

    r = client.post("/flight-watch/api/presets/delta-pvg-lax-nrt-27spring-d0214/import")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["trip_mode"] == "open_jaw"
    assert body["enabled"] is False


if __name__ == "__main__":
    test_mounted_preset_import_without_lifespan()
    print("mounted preset import tests ok")
