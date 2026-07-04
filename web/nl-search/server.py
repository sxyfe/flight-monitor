"""NL Flight Search — FastAPI 本地服务。"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "web" / "shared"))

from subscription_gate import (  # noqa: E402
    check_search_allowed,
    get_user_from_request,
    record_search_usage,
)

from flight_search_engine import (  # noqa: E402
    MatrixSearchIntent,
    RollingGoClient,
    SearchIntent,
    get_country_city_codes,
    probe_flight_pricing,
    search,
    search_airports_for_picker,
    search_matrix,
    validate_intent,
    validate_matrix_intent,
)
from nl_parser import parse_query  # noqa: E402
from viz_export import offers_to_viz_bundle  # noqa: E402

HOST = os.environ.get("NL_SEARCH_HOST", "127.0.0.1")
PORT = int(os.environ.get("NL_SEARCH_PORT", "8765"))
WEB_ROOT = os.environ.get("WEB_ROOT", "").rstrip("/")
CREDENTIALS_FILE = Path(__file__).parent / ".credentials.local.json"


_cors_raw = os.environ.get("ALLOWED_ORIGINS", "").strip()
if _cors_raw:
    _cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
else:
    _cors_origins = [f"http://{HOST}:{PORT}", "http://127.0.0.1:8765"]

app = FastAPI(title="NL Flight Search", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class RollingGoConfig(BaseModel):
    base_url: str = "https://mcp.rollinggo.cn"
    api_key: str = ""


class LlmConfig(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"


class SearchSettings(BaseModel):
    soft_limit_enabled: bool = True
    soft_query_limit: int = 500


class AppConfig(BaseModel):
    rollinggo: RollingGoConfig = Field(default_factory=RollingGoConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)
    search: SearchSettings = Field(default_factory=SearchSettings)


class ParseRequest(BaseModel):
    query: str
    locale: str = "zh-CN"


class SearchRequest(BaseModel):
    intent: dict[str, Any]
    mode: str = "smart"
    confirmed_high_cost: bool = False
    search_type: str = "standard"
    client_request_id: str | None = None


NO_STORE_HEADERS = {"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"}


def _new_stream_nonce() -> str:
    return uuid.uuid4().hex[:16]


def _search_start_response(search_id: str, stream_nonce: str, **extra: Any) -> JSONResponse:
    payload = {
        "search_id": search_id,
        "status": "running",
        "stream_url": f"/api/search/{search_id}/stream",
        "stream_nonce": stream_nonce,
        **extra,
    }
    return JSONResponse(payload, headers=NO_STORE_HEADERS)


class ValidateRequest(BaseModel):
    intent: dict[str, Any]


class MatrixValidateRequest(BaseModel):
    intent: dict[str, Any]


def _validation_dict(v) -> dict[str, Any]:
    return {
        "valid": v.valid,
        "warnings": v.warnings,
        "errors": v.errors,
        "clarifications": v.clarifications,
        "estimated_queries_smart": v.estimated_queries_smart,
        "estimated_queries_exhaustive": v.estimated_queries_exhaustive,
    }


_config = AppConfig()
_searches: dict[str, dict[str, Any]] = {}
_search_lock = threading.Lock()


def _load_credentials():
    global _config
    if CREDENTIALS_FILE.exists():
        try:
            data = json.loads(CREDENTIALS_FILE.read_text())
            _config = AppConfig(**data)
        except Exception:
            pass
    env_rg_key = os.environ.get("ROLLINGGO_API_KEY", "").strip()
    if env_rg_key:
        _config.rollinggo.api_key = env_rg_key
    env_rg_base = os.environ.get("ROLLINGGO_BASE_URL", "").strip()
    if env_rg_base:
        _config.rollinggo.base_url = env_rg_base
    env_llm_key = os.environ.get("LLM_API_KEY", "").strip()
    if env_llm_key:
        _config.llm.api_key = env_llm_key
    env_llm_base = os.environ.get("LLM_BASE_URL", "").strip()
    if env_llm_base:
        _config.llm.base_url = env_llm_base
    env_llm_model = os.environ.get("LLM_MODEL", "").strip()
    if env_llm_model:
        _config.llm.model = env_llm_model
    if not _config.rollinggo.api_key:
        mcp = Path.home() / ".cursor/mcp.json"
        if mcp.exists():
            try:
                data = json.loads(mcp.read_text())
                auth = data["mcpServers"]["RollingGo-Flight"]["headers"]["Authorization"]
                _config.rollinggo.api_key = auth.split(" ", 1)[1]
            except Exception:
                pass


def _save_credentials():
    CREDENTIALS_FILE.write_text(_config.model_dump_json(indent=2))


_load_credentials()


def _rollinggo_client() -> RollingGoClient:
    if not _config.rollinggo.api_key:
        raise HTTPException(400, "RollingGo API Key 未配置")
    return RollingGoClient(_config.rollinggo.base_url, _config.rollinggo.api_key)


def _mcp_rollinggo_client() -> RollingGoClient | None:
    """从 Cursor mcp.json 读取 Key，用于本地凭证失效时重试 RollingGo。"""
    mcp = Path.home() / ".cursor/mcp.json"
    if not mcp.exists():
        return None
    try:
        data = json.loads(mcp.read_text())
        auth = data["mcpServers"]["RollingGo-Flight"]["headers"]["Authorization"]
        key = auth.split(" ", 1)[1].strip()
        base = _config.rollinggo.base_url or "https://mcp.rollinggo.cn"
        if key:
            return RollingGoClient(base, key)
    except Exception:
        pass
    return None


def _optional_rollinggo_client() -> RollingGoClient | None:
    try:
        return _rollinggo_client()
    except HTTPException:
        return None


def _render_index_html() -> HTMLResponse:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    inject = f'<meta name="web-base" content="{WEB_ROOT}" />'
    if 'name="web-base"' not in html:
        html = html.replace("<head>", f"<head>\n    {inject}", 1)
    viz_nav = (
        '<a href="/" class="btn btn-ghost" style="text-decoration:none">首页</a>'
        '<a href="/skill/" class="btn btn-ghost" style="text-decoration:none">Skill</a>'
        if WEB_ROOT
        else ""
    )
    html = html.replace("<!-- VIZ_NAV -->", viz_nav)
    return HTMLResponse(html)


@app.get("/")
async def index():
    return _render_index_html()


@app.get("/nl-search")
async def nl_search_redirect():
    """standalone 本地开发：/nl-search/ 重定向到根路径。"""
    if WEB_ROOT:
        return _render_index_html()
    return RedirectResponse("/", status_code=302)


@app.get("/nl-search/")
async def nl_search_index():
    if WEB_ROOT:
        return _render_index_html()
    return RedirectResponse("/", status_code=302)


@app.get("/api/config")
async def get_config():
    return {
        "rollinggo": {
            "base_url": _config.rollinggo.base_url,
            "api_key": _config.rollinggo.api_key,
        },
        "llm": {
            "base_url": _config.llm.base_url,
            "api_key": _config.llm.api_key,
            "model": _config.llm.model,
        },
        "search": {
            "soft_limit_enabled": _config.search.soft_limit_enabled,
            "soft_query_limit": _config.search.soft_query_limit,
        },
    }


@app.post("/api/config")
async def save_config(cfg: AppConfig):
    global _config
    _config = cfg
    _save_credentials()
    return {"ok": True}


@app.get("/api/config/status")
async def config_status():
    return {
        "rollinggo_configured": bool(_config.rollinggo.api_key),
        "llm_configured": bool(_config.llm.api_key),
        "rollinggo_base_url": _config.rollinggo.base_url,
        "llm_base_url": _config.llm.base_url,
        "llm_model": _config.llm.model,
        "search_soft_limit_enabled": _config.search.soft_limit_enabled,
        "search_soft_query_limit": _config.search.soft_query_limit,
    }


@app.get("/api/country/{country_name}/airports")
async def country_airports(country_name: str, mode: str = "exhaustive"):
    if mode not in ("smart", "exhaustive"):
        raise HTTPException(400, "mode must be smart or exhaustive")
    info = get_country_city_codes(country_name, mode=mode)  # type: ignore[arg-type]
    if not info["codes"] and not info["in_catalog"]:
        raise HTTPException(404, f"未找到国家「{country_name}」的城市目录")
    return info


@app.post("/api/config/test-rollinggo")
async def test_rollinggo():
    client = _rollinggo_client()
    airport = client.search_airports("BJS")
    if "error" in airport:
        raise HTTPException(400, airport["error"])
    if airport.get("success") is False:
        raise HTTPException(400, f"机场搜索失败：{airport.get('message') or '未知错误'}")
    ok, msg = probe_flight_pricing(client)
    if not ok:
        raise HTTPException(400, f"查价服务异常：{msg}")
    return {"ok": True, "message": "RollingGo 机场搜索与航班查价均正常"}


@app.post("/api/config/test-llm")
async def test_llm():
    if not _config.llm.api_key:
        raise HTTPException(400, "LLM API Key 未配置")
    import urllib.request

    url = f"{_config.llm.base_url.rstrip('/')}/chat/completions"
    body = json.dumps(
        {
            "model": _config.llm.model,
            "messages": [{"role": "user", "content": "reply OK"}],
            "max_tokens": 5,
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {_config.llm.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        return {"ok": True, "message": "LLM 连接成功"}
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/intent/parse")
async def intent_parse(req: ParseRequest):
    if not _config.llm.api_key:
        pass  # 允许规则回退
    rg = None
    try:
        rg = _rollinggo_client()
    except HTTPException:
        rg = None
    intent, validation = parse_query(
        req.query,
        _config.llm.base_url,
        _config.llm.api_key or None,
        _config.llm.model,
        rg,
        use_llm=bool(_config.llm.api_key),
    )
    return {
        "intent": intent.to_dict(),
        "validation": _validation_dict(validation),
    }


@app.post("/api/intent/validate")
async def intent_validate(req: ValidateRequest):
    intent = SearchIntent.from_dict(req.intent)
    client = None
    try:
        client = _rollinggo_client()
    except HTTPException:
        pass
    validation = validate_intent(intent, client)
    return {"validation": _validation_dict(validation)}


@app.post("/api/matrix/validate")
async def matrix_validate(req: MatrixValidateRequest):
    intent = MatrixSearchIntent.from_dict(req.intent)
    validation = validate_matrix_intent(intent)
    return {"validation": _validation_dict(validation)}


def _airport_search_error_payload(err: str, *, not_configured: bool = False) -> JSONResponse:
    if not_configured or "401" in err or "403" in err:
        return JSONResponse(
            status_code=401,
            content={
                "items": [],
                "error": (
                    "RollingGo API Key 未配置，请在右上角设置页填写"
                    if not_configured
                    else "RollingGo 认证失败（401），请在设置页更新 API Key"
                ),
                "code": "NOT_CONFIGURED" if not_configured else "ROLLINGGO_AUTH",
            },
        )
    return JSONResponse(
        status_code=400,
        content={"items": [], "error": err or "机场搜索失败", "code": "AIRPORT_SEARCH_FAILED"},
    )


@app.get("/api/airport/search")
async def airport_search(q: str = "", keyword: str = ""):
    """代理 RollingGo MCP searchAirports（keyword）；失败时回退 OurAirports 本地索引。"""
    query = (q or keyword).strip()
    if not query:
        return {"items": [], "source": "none"}

    primary = _optional_rollinggo_client()
    alt = _mcp_rollinggo_client()
    if primary and alt and primary.api_key == alt.api_key:
        alt = None

    result = search_airports_for_picker(primary, query, alt_client=alt)

    if result.get("items"):
        payload: dict[str, Any] = {
            "items": result["items"],
            "source": result.get("source", "rollinggo"),
        }
        if result.get("warning"):
            payload["warning"] = result["warning"]
        return payload

    err = str(result.get("error") or "机场搜索失败")
    if result.get("auth_failed") and not primary and not alt:
        return _airport_search_error_payload(err, not_configured=True)
    if result.get("auth_failed"):
        return _airport_search_error_payload(err)
    return JSONResponse(
        status_code=400,
        content={"items": [], "error": err, "code": "AIRPORT_SEARCH_FAILED", "source": "none"},
    )


def _run_search(search_id: str, intent: SearchIntent, mode: str):
    client = RollingGoClient(_config.rollinggo.base_url, _config.rollinggo.api_key)
    state = _searches[search_id]
    state["offers"] = []
    cancel_event = threading.Event()
    state["cancel_event"] = cancel_event

    def should_cancel() -> bool:
        return cancel_event.is_set()

    def on_progress(done: int, total: int):
        state["progress"] = {"done": done, "total": total, "hits": len(state["offers"])}

    def on_offer(offer: dict[str, Any]):
        state["offers"].append(offer)
        prog = state.get("progress", {})
        state["progress"] = {
            "done": prog.get("done", 0),
            "total": prog.get("total", 0),
            "hits": len(state["offers"]),
        }

    try:
        result = search(
            client,
            intent,
            mode=mode,
            on_progress=on_progress,
            on_offer=on_offer,
            should_cancel=should_cancel,
        )
        if should_cancel():
            state["status"] = "cancelled"
        else:
            state["status"] = "completed"
        state["offers"] = result.offers
        state["aggregations"] = result.aggregations
        state["meta"] = result.meta
        state["stats"] = asdict(result.stats)
        prog = state.get("progress", {})
        state["progress"] = {
            "done": prog.get("done", result.stats.total_queries),
            "total": prog.get("total", result.stats.total_queries),
            "hits": len(result.offers),
            "pricing_service_abnormal": result.stats.pricing_service_abnormal,
            "api_failures": result.stats.api_failures,
        }
        if result.stats.pricing_service_abnormal:
            state["pricing_warning"] = result.stats.api_failure_message or "查价服务异常"
    except Exception as e:
        if should_cancel():
            state["status"] = "cancelled"
        else:
            state["status"] = "error"
            state["error"] = str(e)


def _run_matrix_search(search_id: str, intent: MatrixSearchIntent):
    client = RollingGoClient(_config.rollinggo.base_url, _config.rollinggo.api_key)
    state = _searches[search_id]
    state["offers"] = []
    cancel_event = threading.Event()
    state["cancel_event"] = cancel_event

    def should_cancel() -> bool:
        return cancel_event.is_set()

    def on_progress(done: int, total: int):
        state["progress"] = {"done": done, "total": total, "hits": len(state["offers"])}

    def on_offer(offer: dict[str, Any]):
        state["offers"].append(offer)
        prog = state.get("progress", {})
        state["progress"] = {
            "done": prog.get("done", 0),
            "total": prog.get("total", 0),
            "hits": len(state["offers"]),
        }

    try:
        result = search_matrix(
            client,
            intent,
            on_progress=on_progress,
            on_offer=on_offer,
            should_cancel=should_cancel,
        )
        if should_cancel():
            state["status"] = "cancelled"
        else:
            state["status"] = "completed"
        state["offers"] = result.offers
        state["aggregations"] = result.aggregations
        state["meta"] = result.meta
        state["stats"] = asdict(result.stats)
        prog = state.get("progress", {})
        state["progress"] = {
            "done": prog.get("done", result.stats.total_queries),
            "total": prog.get("total", result.stats.total_queries),
            "hits": len(result.offers),
            "pricing_service_abnormal": result.stats.pricing_service_abnormal,
            "api_failures": result.stats.api_failures,
        }
        if result.stats.pricing_service_abnormal:
            state["pricing_warning"] = result.stats.api_failure_message or "查价服务异常"
    except Exception as e:
        if should_cancel():
            state["status"] = "cancelled"
        else:
            state["status"] = "error"
            state["error"] = str(e)



@app.post("/api/search")
async def start_search(req: SearchRequest, request: Request):
    _rollinggo_client()
    search_type = req.search_type if req.search_type in ("standard", "matrix") else "standard"
    user_id = get_user_from_request(request)

    if search_type == "matrix":
        intent = MatrixSearchIntent.from_dict(req.intent)
        validation = validate_matrix_intent(intent)
        if not validation.valid:
            raise HTTPException(400, {"code": "INVALID_INTENT", "validation": validation.__dict__})
        est = validation.estimated_queries_smart
        gate = check_search_allowed(
            user_id, mode="smart", search_type="matrix", estimated_queries=est
        )
        if not gate.allowed:
            raise HTTPException(
                402,
                {"code": gate.code, "message": gate.message, "upgrade_url": gate.upgrade_url},
            )
        search_id = f"srch_{uuid.uuid4().hex[:12]}"
        stream_nonce = _new_stream_nonce()
        with _search_lock:
            _searches[search_id] = {
                "id": search_id,
                "status": "running",
                "search_type": "matrix",
                "progress": {"done": 0, "total": est, "hits": 0},
                "offers": [],
                "stream_nonce": stream_nonce,
                "stream_consumed": False,
                "client_request_id": req.client_request_id,
                "created_at": time.time(),
            }
        thread = threading.Thread(
            target=_run_matrix_search, args=(search_id, intent), daemon=True
        )
        thread.start()
        record_search_usage(user_id, 1)
        return _search_start_response(search_id, stream_nonce, search_type="matrix")

    client = _rollinggo_client()
    intent = SearchIntent.from_dict(req.intent)
    validation = validate_intent(intent, client)
    if not validation.valid:
        raise HTTPException(400, {"code": "INVALID_INTENT", "validation": validation.__dict__})
    mode = req.mode if req.mode in ("smart", "exhaustive") else "smart"
    est = validation.estimated_queries_exhaustive if mode == "exhaustive" else validation.estimated_queries_smart
    gate = check_search_allowed(
        user_id, mode=mode, search_type="standard", estimated_queries=est
    )
    if not gate.allowed:
        raise HTTPException(
            402,
            {"code": gate.code, "message": gate.message, "upgrade_url": gate.upgrade_url},
        )
    search_id = f"srch_{uuid.uuid4().hex[:12]}"
    stream_nonce = _new_stream_nonce()
    with _search_lock:
        _searches[search_id] = {
            "id": search_id,
            "status": "running",
            "search_type": "standard",
            "progress": {"done": 0, "total": est, "hits": 0},
            "offers": [],
            "mode": mode,
            "stream_nonce": stream_nonce,
            "stream_consumed": False,
            "client_request_id": req.client_request_id,
            "created_at": time.time(),
        }
    thread = threading.Thread(target=_run_search, args=(search_id, intent, mode), daemon=True)
    thread.start()
    record_search_usage(user_id, 1)
    return _search_start_response(search_id, stream_nonce)


@app.post("/api/search/{search_id}/cancel")
async def cancel_search(search_id: str):
    with _search_lock:
        st = _searches.get(search_id)
        if not st:
            raise HTTPException(404, "search not found")
        if st.get("status") != "running":
            return {"ok": False, "message": "搜索未在进行中"}
        ev = st.get("cancel_event")
        if ev:
            ev.set()
    return {"ok": True, "message": "正在停止…"}


@app.get("/api/search/{search_id}")
async def get_search(search_id: str):
    st = _searches.get(search_id)
    if not st:
        raise HTTPException(404, "search not found")
    return st


@app.get("/api/search/{search_id}/viz-bundle")
async def get_search_viz_bundle(search_id: str):
    st = _searches.get(search_id)
    if not st:
        raise HTTPException(404, "search not found")
    if st.get("search_type") == "matrix":
        raise HTTPException(400, "矩阵搜索请使用报告视图，暂不支持雷达导出")
    offers = st.get("offers") or []
    if not offers:
        raise HTTPException(404, "该搜索暂无命中，无法生成雷达数据")
    return offers_to_viz_bundle(
        offers,
        meta=st.get("meta") or {},
        search_id=search_id,
    )


@app.get("/api/search/{search_id}/stream")
async def stream_search(search_id: str, nonce: str | None = None):
    if search_id not in _searches:
        raise HTTPException(404, "search not found")

    with _search_lock:
        st = _searches.get(search_id, {})
        expected_nonce = st.get("stream_nonce")
        if not nonce or not expected_nonce or nonce != expected_nonce:
            raise HTTPException(
                403,
                {
                    "code": "INVALID_STREAM_NONCE",
                    "message": "无效的 stream nonce，请重新发起搜索（POST /api/search）",
                },
            )
        if st.get("stream_consumed"):
            raise HTTPException(
                410,
                {
                    "code": "STREAM_ALREADY_CONSUMED",
                    "message": "该搜索流已结束，请重新发起搜索",
                },
            )

    async def event_gen():
        last_done = -1
        last_offer_idx = 0
        terminal = False
        while True:
            st = _searches.get(search_id, {})
            prog = st.get("progress", {})
            done = prog.get("done", 0)
            total = prog.get("total", 1)
            if done != last_done:
                last_done = done
                yield f"event: progress\ndata: {json.dumps(prog)}\n\n"
            offers = st.get("offers", [])
            while last_offer_idx < len(offers):
                yield f"event: offer\ndata: {json.dumps(offers[last_offer_idx], ensure_ascii=False)}\n\n"
                last_offer_idx += 1
            if st.get("status") == "completed":
                payload = {
                    "search_id": search_id,
                    "stats": st.get("stats"),
                    "offers": st.get("offers", []),
                    "aggregations": st.get("aggregations", {}),
                    "meta": st.get("meta", {}),
                    "pricing_warning": st.get("pricing_warning"),
                }
                yield f"event: completed\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                terminal = True
                break
            if st.get("status") == "cancelled":
                payload = {
                    "search_id": search_id,
                    "stats": st.get("stats"),
                    "offers": st.get("offers", []),
                    "aggregations": st.get("aggregations", {}),
                    "meta": st.get("meta", {}),
                    "cancelled": True,
                    "pricing_warning": st.get("pricing_warning"),
                }
                yield f"event: cancelled\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                terminal = True
                break
            if st.get("status") == "error":
                yield f"event: error\ndata: {json.dumps({'message': st.get('error')})}\n\n"
                terminal = True
                break
            if search_id not in _searches:
                break
            await asyncio.sleep(0.5)

        if terminal:
            with _search_lock:
                live = _searches.get(search_id)
                if live is not None:
                    live["stream_consumed"] = True

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={**NO_STORE_HEADERS, "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host=HOST, port=PORT, reload=False)
