"""
locustfile.py
─────────────
Locust load-testing script for the Arabic Enterprise Finance Document AI Platform.

Simulates realistic concurrent usage patterns:
  - Document listing  (weight 3 — most common)
  - Document upload   (weight 1 — heavy operation)
  - Status polling    (weight 4 — repeated during AI pipeline wait)
  - ERP sync trigger  (weight 1 — post-approval action)

Usage (from backend/ directory with backend running on localhost:8000):
    # First create a reviewer user and set env vars:
    export LOAD_TEST_EMAIL=reviewer@test.com
    export LOAD_TEST_PASSWORD=TestPass123!
    export LOAD_TEST_HOST=http://localhost:8000

    locust -f tests/locustfile.py \
           --headless \
           --users 20 \
           --spawn-rate 4 \
           --run-time 120s \
           --host $LOAD_TEST_HOST \
           --html tests/load_test_report.html

Performance targets:
    - 95th-percentile response time < 4000ms for listing/status endpoints
    - Upload + pipeline trigger < 2000ms (AI pipeline runs async in Celery)
"""

import os
import random
from io import BytesIO

from locust import HttpUser, between, task, events


# ─── Shared state: tracks uploaded document IDs for realistic polling ──────────
_uploaded_ids: list[str] = []

_EMAIL = os.getenv("LOAD_TEST_EMAIL", "reviewer@test.com")
_PASSWORD = os.getenv("LOAD_TEST_PASSWORD", "TestPass123!")

# Minimal but realistic fake Arabic invoice text
_FAKE_INVOICE_BYTES = (
    "فاتورة ضريبية - Tax Invoice\n"
    "المورد: شركة الخليج للتجارة\n"
    "TRN: 100234567890123\n"
    "التاريخ: 2025-06-15\n"
    "الإجمالي: 10500.00 AED\n"
    "ضريبة القيمة المضافة: 500.00 AED\n"
).encode("utf-8")


class DocumentAIUser(HttpUser):
    """Simulates a reviewer interacting with the Document AI Platform."""

    wait_time = between(1, 3)
    _token: str = ""

    def on_start(self):
        """Authenticate and obtain a JWT token before tasks begin."""
        resp = self.client.post(
            "/api/v1/auth/login/access-token",
            data={"username": _EMAIL, "password": _PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="Auth: Login",
        )
        if resp.status_code == 200:
            self._token = resp.json().get("access_token", "")
        else:
            # If auth fails, log a failure but don't crash Locust
            resp.failure(f"Login failed: {resp.status_code} {resp.text[:200]}")

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    # ── Task 1: List Documents (most frequent - simulates dashboard refresh) ──
    @task(3)
    def list_documents(self):
        """GET /api/v1/documents/ — browse the document dashboard."""
        r = self.client.get(
            "/api/v1/documents/?skip=0&limit=20",
            headers=self._auth_headers(),
            name="Docs: List (page 1)",
        )
        if r.status_code == 200:
            docs = r.json()
            # Refresh the global pool of known document IDs
            for doc in docs:
                doc_id = doc.get("id")
                if doc_id and doc_id not in _uploaded_ids:
                    _uploaded_ids.append(doc_id)
            # Trim pool to avoid unbounded growth
            if len(_uploaded_ids) > 500:
                del _uploaded_ids[:100]

    # ── Task 2: Upload a new invoice ──────────────────────────────────────────
    @task(1)
    def upload_invoice(self):
        """POST /api/v1/documents/upload — simulate uploading an Arabic invoice."""
        file_data = BytesIO(_FAKE_INVOICE_BYTES)
        r = self.client.post(
            "/api/v1/documents/upload",
            files={"file": ("invoice_load_test.txt", file_data, "text/plain")},
            headers=self._auth_headers(),
            name="Docs: Upload",
        )
        if r.status_code == 200:
            new_id = r.json().get("id")
            if new_id:
                _uploaded_ids.append(new_id)

    # ── Task 3: Poll document status (most frequent — simulates waiting) ──────
    @task(4)
    def poll_document_status(self):
        """GET /api/v1/documents/{id} — poll processing state for a real document."""
        if not _uploaded_ids:
            # Nothing to poll yet; fall back to listing
            self.list_documents()
            return

        doc_id = random.choice(_uploaded_ids)
        self.client.get(
            f"/api/v1/documents/{doc_id}",
            headers=self._auth_headers(),
            name="Docs: Status Poll",
        )

    # ── Task 4: ERP Sync Trigger ──────────────────────────────────────────────
    @task(1)
    def trigger_erp_sync(self):
        """POST /api/v1/documents/{id}/sync/odoo — test ERP trigger path."""
        if not _uploaded_ids:
            return  # Nothing to sync

        doc_id = random.choice(_uploaded_ids)
        # Expect 400 (not COMPLETED yet) or 200 (if coincidentally done)
        with self.client.post(
            f"/api/v1/documents/{doc_id}/sync/odoo",
            headers=self._auth_headers(),
            name="ERP: Sync Trigger",
            catch_response=True,
        ) as r:
            # Both 400 (not yet complete) and 200 are valid here
            if r.status_code in (200, 400, 404):
                r.success()
            else:
                r.failure(f"Unexpected status {r.status_code}")

    # ── Task 5: Health check ──────────────────────────────────────────────────
    @task(1)
    def health_check(self):
        self.client.get("/health", name="Health Check")


# ─── Load-test summary hook ────────────────────────────────────────────────────

@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    """Print a performance summary and flag SLA failures."""
    stats = environment.runner.stats.total
    p95_ms = stats.get_response_time_percentile(0.95)
    p99_ms = stats.get_response_time_percentile(0.99)
    failure_rate = stats.fail_ratio * 100

    print("\n" + "═" * 60)
    print("  LOAD TEST SUMMARY")
    print("═" * 60)
    print(f"  Total requests   : {stats.num_requests}")
    print(f"  Failures         : {stats.num_failures} ({failure_rate:.1f}%)")
    print(f"  RPS              : {stats.current_rps:.1f}")
    print(f"  P95 Response     : {p95_ms:.0f}ms  (target < 4000ms)")
    print(f"  P99 Response     : {p99_ms:.0f}ms")
    print("─" * 60)

    if p95_ms < 4000:
        print("  ✅  SLA MET: P95 < 4s target achieved")
    else:
        print(f"  ❌  SLA MISS: P95 = {p95_ms:.0f}ms > 4000ms target")
        environment.process_exit_code = 1

    print("═" * 60 + "\n")
