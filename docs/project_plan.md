# Project Plan: Open-Source Arabic Enterprise Finance Document AI Platform

## Phase 1: Initiation and Infrastructure Setup (Days 1-2)

### 1.1 Requirements & Environment Setup
- Finalize technical requirements, constraints, and validation rules (e.g., UAE VAT 5% rules).
- Establish Git repositories, branch strategies, and CI/CD pipelines.
- Configure local development and staging environments.
- Define data security protocols (HTTPS, AES-256 for PostgreSQL storage).

### 1.2 Core Infrastructure Deployment
- Install and configure Docker Desktop and Minikube (or Docker Desktop's built-in Kubernetes) on the local host machine.
- Verify local GPU availability and passthrough configuration for LLMs (NVIDIA Container Toolkit).
- Deploy core backend services locally using Docker Compose:
  - PostgreSQL database with initial schemas (users, documents, extractions, logs).
  - Redis/Celery for task queuing and message brokering.

## Phase 2: Core Backend, Ingestion, & Pre-processing (Days 2-3)

### 2.1 API Development (Document Ingestion)
- Develop FastAPI backend foundation.
- Create REST endpoints for secure document upload (PDF, JPEG, PNG).
- Implement JWT authentication with role-based access control (Admin, Reviewer, Auditor).
- Integrate secure file storage (encrypted at rest).

### 2.2 Pre-processing & Enhancing Pipeline
- Integrate OpenCV for document pre-processing:
  - Deskewing and rotation correction.
  - Noise reduction (denoising).
  - Contrast adjustment and binarization to improve OCR readability.

## Phase 3: OCR and NLP Extraction Engines (Days 4-6)

### 3.1 OCR Layer Integration
- Set up PaddleOCR backend for scalable, parallel processing.
- Configure PaddleOCR models to support mixed Arabic & English layouts.
- Implement extraction of raw text blocks with bounding boxes and character-level confidence scores.

### 3.2 NLP Layer (AraBERT)
- Prepare and anonymize a base dataset of UAE-based enterprise invoices.
- Fine-tune AraBERT for Financial Named Entity Recognition (NER), targeting:
  - Vendor Name
  - TRN (Tax Registration Number)
  - Invoice Date
  - Total Amount
  - VAT Amount
- Develop inference scripts and integrate them into the Celery task queue pipeline.

## Phase 4: Open-Source LLM & Validation Layer (Days 7-9)

### 4.1 Local LLM Serving Setup
- Set up vLLM or Ollama for high-throughput serving of open-weights models (Llama 3 70B or Mistral Large) on GPU nodes.
- Generate synthetic invoice data using prompt engineering for diverse layouts.

### 4.2 LLM Fine-tuning & Validation Engine
- Fine-tune the LLM (using LoRA) on the labeled UAE invoice dataset to structure and validate OCR/NER outputs into JSON format.
- Implement the VAT Validation Engine programmatically to check the 5% UAE math rule, factoring in a configurable tolerance gap for rounding edge cases.
- Implement the Duplicate Detection Module utilizing hash-based document checks and database-level fuzzy matching for vendor, date, and amount.
- Develop the reasoning trace and confidence score aggregation component per field and document.

## Phase 5: Human-in-the-Loop (HITL) Dashboard (Days 10-11)

### 5.1 Dashboard Frontend (Next.js/TypeScript)
- Scaffold a Next.js web application.
- Implement a user-friendly Reviewer UI:
  - Split view containing the original document image and the extracted editable JSON fields.
  - Visual highlighting of low-confidence fields based on PaddleOCR/LLM aggregated scores.

### 5.2 Confidence Routing & Feedback Loop
- Configure routing logic: invoices scoring below 95% threshold are pushed to the HITL Review Queue.
- Establish the active learning feedback loop to save human-corrected outputs back to a specific dataset for future model retraining (AraBERT and LLM LoRA weight updates).
- Implement robust audit trail logging reflecting who made corrections and when.

## Phase 6: ERP Integration & Connectors (Day 12)

### 6.1 Connector Development
- Build extensible integration adapters over the core API.
- Develop standard open-source ERP connectors for easy export to:
  - Odoo
  - ERPNext
  - Dolibarr
- Ensure the connector logic handles authentication, payload mapping, and automated error retries.

## Phase 7: Testing, Auditing, & Optimization (Day 13)

### 7.1 Quality Assurance
- Execute End-to-End (E2E) feature testing on staging environments using real-world anonymized sample caches.
- Validate the rule-based math checks and duplicate detection edge cases.
- Performance testing to hit target metrics (processing time < 4 seconds per page, accuracy > 93%).

### 7.2 Security & Compliance Check
- Perform a thorough internal security audit against UAE NESA and ISO 27001 guidelines controls.
- Confirm secure encryption handling and RBAC JWT scoping.

## Phase 8: Deployment & Handover (Day 14)

### 8.1 Local Production Deployment
- Finalize local Docker Compose definitions for rapid spins and teardowns.
- Configure local Kubernetes manifest files (Minikube).
- Execute full local deployment of all microservices, databases, caching layers, and LLM inference endpoints.
- Configure monitoring using Prometheus to ingest metric data, and Grafana to visualize inference latency, OCR queue lengths, and server resources.

### 8.2 Documentation & Handover
- Finalize internal codebase documentation via docstrings & Markdown files.
- Produce Admin and Reviewer User Manuals for interacting with the HITL Dashboard.
- Conduct onboarding and final feature handovers to key project stakeholders.
