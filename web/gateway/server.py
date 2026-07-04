"""Flight Monitor 统一 Web 网关：官网 + nl-search + flight-watch + billing。"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

WEB = Path(__file__).resolve().parent.parent
ROOT = WEB.parent

sys.path.insert(0, str(ROOT / "scripts"))

os.environ.setdefault("WEB_ROOT", "/nl-search")


def _load_subapp(module_name: str, app_dir: Path):
    app_dir_str = str(app_dir)
    if app_dir_str not in sys.path:
        sys.path.append(app_dir_str)
    spec = importlib.util.spec_from_file_location(module_name, app_dir / "server.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {app_dir / 'server.py'}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.app


nl_app = _load_subapp("nl_search_server", WEB / "nl-search")
fw_app = _load_subapp("flight_watch_server", WEB / "flight-watch")
billing_app = _load_subapp("billing_server", WEB / "billing")

app = FastAPI(title="Flight Monitor Web", version="1.1.0")
LANDING_DIR = WEB / "landing"
SKILL_DIR = LANDING_DIR / "skill"


@app.get("/nl-search")
async def nl_search_redirect():
    return RedirectResponse("/nl-search/", status_code=302)


@app.get("/skill")
async def skill_redirect():
    return RedirectResponse("/skill/", status_code=302)


@app.get("/flight-watch")
async def flight_watch_redirect():
    return RedirectResponse("/flight-watch/", status_code=302)


@app.get("/billing")
async def billing_redirect():
    return RedirectResponse("/billing/", status_code=302)


app.mount("/billing", billing_app)
app.mount("/nl-search", nl_app)
app.mount("/flight-watch", fw_app)
app.mount("/skill", StaticFiles(directory=SKILL_DIR, html=True), name="skill")
app.mount("/", StaticFiles(directory=LANDING_DIR, html=True), name="landing")
