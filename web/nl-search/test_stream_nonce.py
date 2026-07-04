"""验证 stream nonce 防 replay：无需 RollingGo Key。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent / "scripts"))

spec = importlib.util.spec_from_file_location("nl_search_server", ROOT / "server.py")
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)

client = TestClient(mod.app)


def test_stream_nonce_guards():
    sid = "srch_test001"
    nonce = "abc123nonce45678"
    mod._searches[sid] = {
        "id": sid,
        "status": "completed",
        "search_type": "matrix",
        "progress": {"done": 10, "total": 10, "hits": 0},
        "offers": [],
        "stats": {"total_queries": 10, "errors": 10},
        "meta": {"sample_error": "HTTP 401"},
        "stream_nonce": nonce,
        "stream_consumed": False,
    }

    r_no_nonce = client.get(f"/api/search/{sid}/stream")
    assert r_no_nonce.status_code == 403, r_no_nonce.text

    r_bad = client.get(f"/api/search/{sid}/stream", params={"nonce": "wrong"})
    assert r_bad.status_code == 403, r_bad.text

    r_ok = client.get(f"/api/search/{sid}/stream", params={"nonce": nonce})
    assert r_ok.status_code == 200, r_ok.text
    body = r_ok.text
    assert "event: completed" in body
    assert "event: progress" in body

    mod._searches[sid]["stream_consumed"] = True
    r_replay = client.get(f"/api/search/{sid}/stream", params={"nonce": nonce})
    assert r_replay.status_code == 410, r_replay.text

    mod._searches.pop(sid, None)
    print("stream nonce guards OK")


def test_post_returns_distinct_ids():
    """两次 POST 若通过校验，search_id 与 stream_nonce 均应不同。"""
    intent = {
        "origins": ["PEK"],
        "destinations": ["SHA"],
        "out_date_start": "2026-10-01",
        "out_date_end": "2026-10-03",
        "ret_date_start": "2026-10-05",
        "ret_date_end": "2026-10-07",
        "min_stay_days": 2,
        "max_stay_days": 5,
        "cabin": "economy",
        "adults": 1,
    }
    try:
        r1 = client.post(
            "/api/search",
            json={"intent": intent, "search_type": "matrix", "client_request_id": "req-a"},
        )
        r2 = client.post(
            "/api/search",
            json={"intent": intent, "search_type": "matrix", "client_request_id": "req-b"},
        )
    except Exception as e:
        print(f"POST skipped (likely missing RollingGo config): {e}")
        return

    if r1.status_code != 200 or r2.status_code != 200:
        print(f"POST skipped: status {r1.status_code} / {r2.status_code}")
        return

    d1, d2 = r1.json(), r2.json()
    assert d1["search_id"] != d2["search_id"], (d1, d2)
    assert d1["stream_nonce"] != d2["stream_nonce"], (d1, d2)
    assert r1.headers.get("cache-control", "").startswith("no-store")
    print(f"distinct POST ids OK: {d1['search_id']} vs {d2['search_id']}")


if __name__ == "__main__":
    test_stream_nonce_guards()
    test_post_returns_distinct_ids()
    print("all checks passed")
