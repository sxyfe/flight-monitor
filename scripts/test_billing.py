#!/usr/bin/env python3
"""订阅计费模块单元测试。"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BILLING = ROOT / "web" / "billing"
sys.path.insert(0, str(BILLING))

os.environ["BILLING_ENABLED"] = "true"
os.environ["BILLING_MOCK_PAY"] = "true"


class BillingTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db = Path(self._tmpdir.name) / "billing.db"
        os.environ["BILLING_DB_PATH"] = str(db)
        import store

        store.DB_PATH = db
        store.init_db()
        self.store = store

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_register_grants_free_trial(self):
        from auth import hash_password

        user = self.store.create_user("test@example.com", hash_password("secret1"))
        sub = self.store.get_active_subscription(user["id"])
        self.assertIsNotNone(sub)
        self.assertEqual(sub["plan_id"], "free_trial")

    def test_search_quota_gate(self):
        from auth import hash_password
        from entitlements import check_search_allowed, record_search_usage

        user = self.store.create_user("q@example.com", hash_password("secret1"))
        uid = user["id"]
        gate = check_search_allowed(uid, mode="exhaustive")
        self.assertFalse(gate.allowed)
        self.assertEqual(gate.code, "PLAN_LIMIT")

        gate2 = check_search_allowed(uid, estimated_queries=5)
        self.assertTrue(gate2.allowed)
        for _ in range(30):
            record_search_usage(uid, 1)
        gate3 = check_search_allowed(uid, estimated_queries=1)
        self.assertFalse(gate3.allowed)
        self.assertEqual(gate3.code, "QUOTA_EXCEEDED")

    def test_mock_checkout_flow(self):
        from auth import hash_password
        import stripe_pay
        from plans import PLANS

        user = self.store.create_user("pay@example.com", hash_password("secret1"))
        order = self.store.create_order(user["id"], "week", PLANS["week"].price_cny)
        result = stripe_pay.complete_mock_order(order["id"])
        self.assertTrue(result["ok"])
        sub = self.store.get_active_subscription(user["id"])
        self.assertEqual(sub["plan_id"], "week")

    def test_plans_public(self):
        from plans import list_plans_public

        plans = list_plans_public()
        self.assertEqual(len(plans), 6)
        ids = {p["id"] for p in plans}
        self.assertIn("lifetime", ids)


if __name__ == "__main__":
    unittest.main()
