# Human-in-the-Loop (HITL) Dashboard: Admin Manual

As an Administrator of the Arabic Enterprise Finance Document AI Platform, your responsibilities extend beyond standard review. You govern access, orchestrate ERP synchronization, manage AI active learning datasets, and audit system integrity.

## 1. System Access & RBAC Controls

The backend strictly enforces JWT-based Role-Based Access Control via `app/core/security.py`.
- Ensure newly onboarded Reviewer accounts are set to `is_active=True` and `is_reviewer=True` directly in the database.
- Normal Reviewers **cannot** push configurations to ERP APIs or delete data.

## 2. Monitoring the Document Processing Queue (Celery)
The system relies heavily on asynchronous Celery background workers to avoid blocking the main FastAPI process while processing heavy ML models (PaddleOCR / AraBERT / Ollama).
Administrators should monitor the Celery task performance to ensure 4-second latency SLA limits are actively maintained:
- **`app.worker.process_document`**: The primary document AI ingestion pipeline.
- **`app.worker.erp_sync_task`**: The auto-retrying queue communicating with the ERP APIs.

### 2.1 Viewing Metrics
Open `http://localhost:3000` (Grafana context - once fully mapped on staging infrastructure) to monitor active Queue depth and Prometheus throughput latency.

## 3. Auditing Reviewer Data 
When Reviewers modify AI extractions on the HITL Dashboard, an immutable transaction replaces the JSON block. An immediate row is generated in the `DocumentAuditLog` database table.

Admins can directly query this to trace issues:
```sql
SELECT document_id, user_id, previous_state, new_state, timestamp 
FROM documentauditlog 
WHERE document_id = 'uuid';
```

## 4. Triggering the Active Learning Feedback Loop
The AI models inside the pipeline actively improve when fed high-quality, verified human corrections.
As an admin, after a significant batch of invoices has been corrected and marked as `COMPLETED`:

1. Send a `GET` request to your API at `http://localhost:8000/api/v1/documents/export/training-data` (requires Admin JWT header).
2. The server spins up a direct pipeline translating the original raw OCR extraction arrays coupled with the *human-corrected JSON* into a structured **JSONL file**.
3. Use this JSONL output block directly to fine-tune your instance of `Ollama Llama-3/Mistral` via LoRA weights, dramatically decreasing Hallucinations for future invoices.

## 5. Connecting & Executing ERP Synchronization
When documents hit `COMPLETED`, they are ready. But until synchronized, the downstream accounts payable platform will not cut a check.

The system natively supports Odoo, ERPNext, and Dolibarr adapters dynamically executed by `Celery`.
- Using `.env` server variables, ensure the `*URL`, `*USERNAME` / `*API_KEY` configurations match the staging environment.
- Send the Sync Instruction:
```bash
POST /api/v1/documents/{document_id}/sync/{provider=odoo|erpnext|dolibarr}
# Header: Bearer <Admin_JWT>
```
If the Dolibarr/Odoo sandbox briefly reboots during a sync attempt, **do not manually restart the process**—the Celery `erp_sync_task` automatically caches the HTTP exception and exponentially retries 5 times.
