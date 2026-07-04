"""网关 mount 场景：子应用 POST 请求体（Pydantic）可正常解析。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "scripts"))


def _load_gateway():
    spec = importlib.util.spec_from_file_location("gateway_server_test", WEB / "gateway" / "server.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gateway_server_test"] = mod
    spec.loader.exec_module(mod)
    return mod.app


def test_mounted_matrix_validate():
    from fastapi.testclient import TestClient

    client = TestClient(_load_gateway())
    r = client.post(
        "/nl-search/api/matrix/validate",
        json={
            "intent": {
                "origins": ["PEK"],
                "destinations": ["NRT"],
                "out_date_start": "2026-07-10",
                "out_date_end": "2026-07-15",
                "ret_date_start": "2026-07-20",
                "ret_date_end": "2026-07-25",
                "min_stay_days": 1,
            }
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["validation"]["valid"] is True


if __name__ == "__main__":
    test_mounted_matrix_validate()
    print("mounted POST tests ok")
