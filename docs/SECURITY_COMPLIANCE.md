# Security & Compliance Audit Report
## Open-Source Arabic Enterprise Finance Document AI Platform

This document outlines the security architecture and procedural implementations that align the platform's infrastructure with **ISO 27001** and **UAE NESA (National Electronic Security Authority)** standards.

## 1. Information Security Policies & Access Control (ISO 27001: A.5, A.9)

### 1.1 Role-Based Access Control (RBAC)
The platform enforces a strict Least-Privilege model through Asymmetric JWT (JSON Web Tokens). 
Users are explicitly segmented into distinct permission pillars mapped to table records in `app.models.user.User`:
- **`is_active: bool`**: General user constraint.
- **`is_reviewer: bool`**: Grants read/write mutation permissions to the `Document` and `DocumentAuditLog` structures in the HITL UI. Access to `/documents/{id}/sync/{provider}` via Celery is reserved for this tier.
- **`is_superuser: bool`**: Administrative override, bypassing frontend middleware constraints.

## 2. Cryptography & Data Protection (UAE NESA: IA.5, ISO 27001: A.10)

### 2.1 Encryption at Rest
- **Database Vaults**: The `idp_db` PostgreSQL container is actively vaulted utilizing persistent volume mounts (`/var/lib/postgresql/data`). It is recommended to deploy this volume mount on a host-level LUKS (Linux Unified Key Setup) or AWS EBS encrypted storage block with AES-256 underlying encryption.
- **LLM Output & User Credentials**: User passwords are cryptographically salted and hashed employing `bcrypt` via the `passlib` context (`app/core/security.py`), nullifying rainbow table compromises.

### 2.2 Encryption in Transit
- The API is strictly built on top of FastAPI and Uvicorn. While HTTP operates via `http://localhost:8000` locally, the reverse proxy configuration is defined to route exclusively through mutual-TLS (mTLS) or HTTPS offloading load-balancers (e.g., NGINX/Traefik with cert-manager) in the Kubernetes deployment manifests.

## 3. Operational Security & Audit Logging (ISO 27001: A.12.4, NESA: OP.3)

### 3.1 Immutable Audit Trails
Any modification to the finalized LLM output made by an `is_reviewer` user strictly logs a comprehensive and immutable trail in the `DocumentAuditLog` table. This tracks:
- **Identifier**: `document_id`, `user_id`
- **Delta Payloads**: `previous_state`, `new_state`
- **Timestamping**: Enforced via standard UTC (`timezone.utc`).

### 3.2 Duplicate Document Hash Mitigation
The backend mitigates document injection/replay attacks (uploading the same fraudulent invoice twice) by enforcing a dual-layer Deduplication Engine:
- **Hashing**: `compute_document_hash(file_path)`
- **Semantic DB Fuzzy Matching**: If `vendor_name`, `invoice_date`, and `total_amount` map natively, the invoice is blocked until manually unblocked by an Admin.

## 4. Supplier Relationships & Data Residency (NESA: SA.4, ISO 27001: A.15)

### 4.1 On-Premise Execution
Under UAE regulatory data residency guidelines (e.g., for Federal/Financial Enterprise Data in abu dhabi/Dubai), **no data leaves the virtual private cloud**. 
- **OCR Engine**: Local `PaddleOCR` (No Google Vision / AWS Textract).
- **NLP Engine**: Downloaded Arabic `transformers` / `AraBERT` pipeline running directly in-memory in the Celery worker queue.
- **LLM Reshaping**: `Ollama` running completely locally without contacting OpenAI APIs or external telemetry brokers.

## Conclusion
The **Arabic Enterprise Finance Document AI Platform** satisfies critical baseline compliance controls regarding authentication schemas, non-repudiation, and encryption mapping for localized, high-security regional deployment scenarios.
