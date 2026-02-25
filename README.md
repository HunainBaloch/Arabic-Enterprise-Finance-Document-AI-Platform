# Arabic Enterprise Finance Document AI Platform

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Next.js](https://img.shields.io/badge/next.js-14-black.svg)

An open-source, full-stack Human-in-the-Loop (HITL) AI platform designed specifically to securely extract, validate, and process Arabic/English bilingual enterprise financial documents (invoices, receipts).

## 🌟 Key Features

*   **Bilingual OCR Engine:** Seamlessly extracts text and figures from documents blending Arabic and English using **Tesseract OCR / pyTesseract** combined with PyMuPDF for high-speed, CPU-optimized processing.
*   **Specialized Arabic NER:** Utilizes a custom fine-tuned **AraBERT** model (F1: 1.00) to precisely identify UAE-specific entities: `VENDOR`, `TRN`, `DATE`, `TOTAL`, and `VAT`.
*   **VAT Rule Validation Engine:** Automatically applies UAE 5% VAT mathematical validations (with configurable rounding tolerances).
*   **Duplicate Detection:** Avoids duplicate invoices via robust MD5 hardware hashing combined with fuzzy AI field-matching.
*   **HITL (Human-in-the-Loop) Dashboard:** Next.js reviewer portal for edge cases where OCR or NLP confidence scores drop below 95%.
*   **Observability & Telemetry:** Built-in Prometheus `/metrics` scraping and a fully configured Grafana dashboard tracking API latency, Celery queues, and system loads.
*   **ERP Sync Ready:** API models prepared for one-click synchronization to open-source ERP systems (Odoo, ERPNext, Dolibarr).

## 📁 Repository Structure

```text
.
├── backend/               # FastAPI backend, Celery workers, NLP/OCR services, tests
├── frontend/              # Next.js Human-in-the-Loop (HITL) dashboard
├── docs/                  # Architectural guides, compliance docs, and user manuals
├── grafana/               # Auto-provisioning configs for Grafana
├── docker-compose.yml     # Local orchestration stack
└── start.ps1              # Automated Windows quick-start script
```

## 🚀 Quick Start (Docker Compose)

### 1. Prerequisites
*   Docker & Docker Compose (or native Python 3.11 with Node.js)
*   **Tesseract OCR** system binary installed (with Arabic language packs: `tesseract-ocr-ara`)
*   (Optional but recommended) NVIDIA GPU with latest drivers for faster AraBERT NER inference

### 2. Startup Script
A fully automated PowerShell startup script is provided for Windows developers:
```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```
*(This script will auto-copy settings from `.env.example`, launch infrastructure, run database migrations, and boot the entire stack).*

### 3. Access Services
Once the script completes, access the stack locally:
*   **HITL Dashboard:** `http://localhost:3000`
*   **API Swagger UI:** `http://localhost:8000/api/v1/docs`
*   **Grafana Dashboards:** `http://localhost:3001` *(default: admin / Grafana_IDP_2026)*

## 📚 Documentation & Guides

Comprehensive documentation is located in the `/docs` directory:
- [Developer Guide](docs/DEVELOPER_GUIDE.md) - Local setup, architecture, and prompt engineering.
- [Project Plan](docs/project_plan.md) - Strategic roadmap and phased milestones.
- [Security & Compliance](docs/SECURITY_COMPLIANCE.md) - UAE NESA & ISO 27001 mapping.
- [Admin Manual](docs/USER_MANUAL_ADMIN.md) / [Reviewer Manual](docs/USER_MANUAL_REVIEWER.md) - Operational guidelines.
- [Completion Report](docs/COMPLETION_REPORT.md) - Executive summary of final build state.

## 🧠 Fine-Tuning AraBERT Locally

Want to re-train the Named Entity Recognition model on your own invoices?
```bash
cd backend/training
# Generates 250 synthetic bilingual invoices
python generate_synthetic_data.py
# Kicks off HuggingFace Trainer (auto-detects RTX 40+ GPUs)
python finetune_arabert.py
```
*The `nlp.py` service will automatically detect and load the model on next restart.*

## 🧪 Testing

The platform maintains 100% test pass status across its validation and deduplication modules.
```bash
cd backend
python -m pytest tests/ -v
```

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for more information.
