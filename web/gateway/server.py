"""Flight Monitor 统一 Web 网关：同一域名下提供 exhaustive-viz 与 nl-search。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

WEB = Path(__file__).resolve().parent.parent
ROOT = WEB.parent

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(WEB / "nl-search"))

os.environ.setdefault("WEB_ROOT", "/nl-search")

import server as nl_server  # noqa: E402

app = FastAPI(title="Flight Monitor Web", version="1.0.0")
VIZ_DIR = WEB / "exhaustive-viz"


@app.get("/nl-search")
async def nl_search_redirect():
    return RedirectResponse("/nl-search/", status_code=302)


app.mount("/nl-search", nl_server.app)
app.mount("/", StaticFiles(directory=VIZ_DIR, html=True), name="viz")
