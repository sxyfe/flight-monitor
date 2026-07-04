"""Flight Watch — 独立 Web 机票监控。"""
from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
ROOT = APP_DIR.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flight_search_engine import RollingGoClient  # noqa: E402

import store  # noqa: E402
from scheduler import (  # noqa: E402
    load_credentials,
    poll_all,
    poll_watch,
    refresh_scheduler_jobs,
    start_scheduler,
)
from store import (  # noqa: E402
    create_watch,
    delete_watch,
    get_watch,
    latest_snapshot,
    list_snapshots,
    list_watches,
    set_watch_enabled,
    update_watch,
)

HOST = os.environ.get("FLIGHT_WATCH_HOST", "127.0.0.1")
PORT = int(os.environ.get("FLIGHT_WATCH_PORT", "8767"))
CREDENTIALS_FILE = APP_DIR / ".credentials.local.json"
PRESETS_FILE = APP_DIR / "presets" / "delta-open-jaw.json"
STATIC_DIR = APP_DIR / "static"


class RollingGoConfig(BaseModel):
    base_url: str = "https://mcp.rollinggo.cn"
    api_key: str = ""


class NotifyConfig(BaseModel):
    feishu_webhook: str = ""
    pushplus_token: str = ""


class AppConfig(BaseModel):
    rollinggo: RollingGoConfig = Field(default_factory=RollingGoConfig)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)


class WatchPayload(BaseModel):
    name: str
    enabled: bool = True
    trip_mode: str
    legs: list[dict[str, str]]
    return_date: str | None = None
    pricing_mode: str = "auto"
    sales_region: str | None = None
    currency: str = "CNY"
    filters: dict[str, Any] = Field(default_factory=dict)
    alerts: dict[str, Any]
    schedule: dict[str, Any] = Field(default_factory=lambda: {"interval_hours": 12})
    reference_price: float | None = None
    notes: str | None = None


class RunOncePayload(BaseModel):
    dry_run: bool = False
    watch_id: str | None = None


_config = AppConfig()


def _normalize_api_key(key: str) -> str:
    key = (key or "").strip()
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    return key


def _load_credentials_file() -> None:
    global _config
    if CREDENTIALS_FILE.exists():
        try:
            _config = AppConfig(**json.loads(CREDENTIALS_FILE.read_text()))
        except Exception:
            pass
    _config.rollinggo.api_key = _normalize_api_key(_config.rollinggo.api_key)
    if not _config.rollinggo.api_key:
        mcp = Path.home() / ".cursor" / "mcp.json"
        if mcp.exists():
            try:
                data = json.loads(mcp.read_text())
                auth = data["mcpServers"]["RollingGo-Flight"]["headers"]["Authorization"]
                _config.rollinggo.api_key = _normalize_api_key(
                    auth.split(" ", 1)[1] if " " in auth else auth
                )
            except Exception:
                pass


def _save_credentials_file() -> None:
    CREDENTIALS_FILE.write_text(_config.model_dump_json(indent=2))


_load_credentials_file()


def _rollinggo_client() -> RollingGoClient:
    if not _config.rollinggo.api_key:
        raise HTTPException(400, "RollingGo API Key 未配置")
    return RollingGoClient(_config.rollinggo.base_url, _config.rollinggo.api_key)


def _client_factory():
    return _rollinggo_client()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    store.init_db()
    creds = load_credentials()
    if creds.get("rollinggo", {}).get("api_key") or _config.rollinggo.api_key:
        try:
            start_scheduler(_client_factory)
        except Exception:
            pass
    yield


app = FastAPI(title="Flight Watch", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{HOST}:{PORT}", "http://127.0.0.1:8767"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/config")
async def get_config():
    return _config.model_dump()


@app.post("/api/config")
async def save_config(cfg: AppConfig):
    global _config
    cfg.rollinggo.api_key = _normalize_api_key(cfg.rollinggo.api_key)
    _config = cfg
    _save_credentials_file()
    refresh_scheduler_jobs(_client_factory)
    return {"ok": True}


@app.get("/api/config/status")
async def config_status():
    return {
        "rollinggo_configured": bool(_config.rollinggo.api_key),
        "feishu_configured": bool(_config.notify.feishu_webhook),
        "pushplus_configured": bool(_config.notify.pushplus_token),
    }


@app.post("/api/config/test-rollinggo")
async def test_rollinggo():
    from flight_search_engine import is_rollinggo_airport_auth_error, probe_flight_pricing

    client = _rollinggo_client()
    airport = client.search_airports("BJS")
    if "error" in airport:
        if is_rollinggo_airport_auth_error(airport):
            raise HTTPException(400, "RollingGo API Key 无效或已过期，请确认 Key 后先保存再测试")
        raise HTTPException(400, airport["error"])
    if airport.get("success") is False:
        msg = airport.get("message") or "未知错误"
        if is_rollinggo_airport_auth_error(airport):
            raise HTTPException(400, "RollingGo API Key 无效或已过期，请确认 Key 后先保存再测试")
        raise HTTPException(400, f"机场搜索失败：{msg}")
    ok, msg = probe_flight_pricing(client)
    if not ok:
        if "401" in msg or "403" in msg or "Unauthorized" in msg:
            raise HTTPException(400, "RollingGo API Key 无效或已过期，请确认 Key 后先保存再测试")
        raise HTTPException(400, f"查价服务异常：{msg}")
    return {"ok": True, "message": "RollingGo 机场搜索与航班查价均正常"}


@app.post("/api/config/test-feishu")
async def test_feishu():
    url = _config.notify.feishu_webhook
    if not url:
        raise HTTPException(400, "飞书 Webhook 未配置")
    from notify.feishu import send_test

    return {"ok": True, "message": send_test(url)}


@app.post("/api/config/test-pushplus")
async def test_pushplus():
    token = _config.notify.pushplus_token
    if not token:
        raise HTTPException(400, "PushPlus token 未配置")
    from notify.pushplus import send_test

    return {"ok": True, "message": send_test(token)}


@app.get("/api/airports/search")
async def airport_search(q: str = ""):
    if not q.strip():
        return {"items": []}
    client = _rollinggo_client()
    data = client.search_airports(q.strip())
    if "error" in data:
        raise HTTPException(400, data["error"])
    items = []
    for item in data.get("airPortInformationList") or []:
        items.append(
            {
                "cityCode": item.get("cityCode"),
                "cityName": item.get("cityName"),
                "airportCode": item.get("airportCode"),
                "airportName": item.get("airportName"),
            }
        )
    return {"items": items}


def _watch_summary(w) -> dict[str, Any]:
    snap = latest_snapshot(w.id)
    d = w.to_dict()
    d["latest_snapshot"] = snap
    return d


@app.get("/api/watches")
async def api_list_watches():
    return {"items": [_watch_summary(w) for w in list_watches()]}


@app.post("/api/watches")
async def api_create_watch(payload: WatchPayload):
    watch = create_watch(payload.model_dump())
    refresh_scheduler_jobs(_client_factory)
    return _watch_summary(watch)


@app.get("/api/watches/{watch_id}")
async def api_get_watch(watch_id: str):
    w = get_watch(watch_id)
    if not w:
        raise HTTPException(404, "未找到监控")
    return _watch_summary(w)


@app.put("/api/watches/{watch_id}")
async def api_update_watch(watch_id: str, payload: WatchPayload):
    w = update_watch(watch_id, payload.model_dump())
    if not w:
        raise HTTPException(404, "未找到监控")
    refresh_scheduler_jobs(_client_factory)
    return _watch_summary(w)


@app.delete("/api/watches/{watch_id}")
async def api_delete_watch(watch_id: str):
    if not delete_watch(watch_id):
        raise HTTPException(404, "未找到监控")
    refresh_scheduler_jobs(_client_factory)
    return {"ok": True}


@app.post("/api/watches/{watch_id}/enable")
async def api_enable_watch(watch_id: str, enabled: bool = True):
    if not get_watch(watch_id):
        raise HTTPException(404, "未找到监控")
    set_watch_enabled(watch_id, enabled)
    refresh_scheduler_jobs(_client_factory)
    return {"ok": True, "enabled": enabled}


@app.post("/api/watches/{watch_id}/poll")
async def api_poll_watch(watch_id: str, dry_run: bool = False):
    try:
        result = poll_watch(watch_id, dry_run=dry_run, client_factory=_client_factory)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    w = get_watch(watch_id)
    return {"watch": _watch_summary(w) if w else None, "poll": result}


@app.get("/api/watches/{watch_id}/snapshots")
async def api_snapshots(watch_id: str, limit: int = 50):
    if not get_watch(watch_id):
        raise HTTPException(404, "未找到监控")
    return {"items": list_snapshots(watch_id, limit=limit)}


@app.post("/api/watch/run-once")
async def api_run_once(body: RunOncePayload):
    if body.watch_id:
        result = poll_watch(body.watch_id, dry_run=body.dry_run, client_factory=_client_factory)
        return {"poll": result}
    return poll_all(dry_run=body.dry_run, client_factory=_client_factory)


@app.get("/api/presets")
async def api_presets():
    if not PRESETS_FILE.exists():
        return {"items": []}
    data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    return {"items": data.get("presets", [])}


@app.post("/api/presets/import-all")
async def api_import_all_presets():
    if not PRESETS_FILE.exists():
        raise HTTPException(404, "预设库不存在")
    data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    created = []
    for preset in data.get("presets", []):
        payload = {**preset, "enabled": False, "name": preset.get("name", preset.get("id", "预设"))}
        payload.pop("id", None)
        watch = create_watch(payload)
        created.append(_watch_summary(watch))
    refresh_scheduler_jobs(_client_factory)
    return {"items": created, "count": len(created)}


@app.post("/api/presets/{preset_id}/import")
async def api_import_preset(preset_id: str):
    if not PRESETS_FILE.exists():
        raise HTTPException(404, "预设库不存在")
    data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    preset = next((p for p in data.get("presets", []) if p["id"] == preset_id), None)
    if not preset:
        raise HTTPException(404, "未找到预设")
    payload = {**preset, "enabled": False, "name": preset.get("name", preset_id)}
    payload.pop("id", None)
    watch = create_watch(payload)
    return _watch_summary(watch)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host=HOST, port=PORT, reload=False)
