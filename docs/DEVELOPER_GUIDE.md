# Developer Guide: Run & Test with Actual Integrations

This guide explains how to fully spin up the **Arabic Enterprise Finance Document AI Platform**, properly secure the deployment using environment variables (`.env`), and execute an End-to-End (E2E) test with live AI integrations (PaddleOCR, AraBERT, Ollama) and ERP Sync triggers.

---

## 1. Prerequisites

Before starting, ensure you have the following installed on your host machine:

- **Docker Desktop** (for PostgreSQL, Redis)
- **Node.js 18+** (for Next.js frontend)
- **Python 3.10+**
- **Ollama** (for local LLM validation)
- **Poppler** (Required for PDF to Image conversion. Install via `apt-get install poppler-utils` on Linux, `brew install poppler` on macOS, or download binaries and add to PATH on Windows).

---

## 2. Security & Environment Setup (`.env`)

For robust security, avoid hardcoding database passwords and JWT secrets.

### 2.1 Copy the Environment Template
At the root of the project, duplicate the `.env.example` file and rename it to `.env`:

```bash
cp .env.example .env
```

### 2.2 Secure the Variables
Open the new `.env` file and **modify the following critical values**:

1. **`SECRET_KEY`**: Generate a strong AES-256 JWT key (e.g., run `openssl rand -hex 32` in your terminal) and paste it here.
2. **`POSTGRES_PASSWORD`**: Change `postgres` to a complex, dedicated password.
3. **`LLM_MODEL`**: Set the model you wish to use via Ollama (e.g., `llama3:8b`, `mistral`).
4. **ERP Variables**: If you are testing ERP sync, append your explicit ERP Keys directly here (e.g., `ODOO_URL=`, `ODOO_PASSWORD=`, `ERPNEXT_API_KEY=`).

*Notice: Ensure that `.env` is listed within your `.gitignore` file so it is never committed to GitHub.*

---

## 3. Launching Core Infrastructure

We rely on Docker for our database (`idp_db`) and message broker (`idp_redis`).

```bash
# From the project root, launch the required services in detached mode
docker-compose up -d db redis
```
Verify they are running by typing `docker ps`.

Once PostgreSQL is up, initialize the database schema by generating and running the Alembic migrations:
```bash
cd backend
python -m alembic upgrade head
```

---

## 4. Running the FastApi Backend & Celery Worker

The platform utilizes a dual-process Python architecture. You must spin up both the FastAPI web server, and the Celery background task worker that handles the heavy OCR/NLP pipeline.

### 4.1. Start the API Server
Ensure your python virtual environment is activated and dependencies installed.

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*The API is now running at `http://localhost:8000`.*

### 4.2. Start the Celery Worker
In a **new terminal tab** (also inside the `/backend` folder), launch the Celery consumer:

```bash
# On Windows
celery -A app.core.celery_app worker -n worker@%h -l info -P solo

# On Linux/macOS
celery -A app.core.celery_app worker -n worker@%h -l info
```
*You should see Celery successfully connect to `redis://localhost:6379/0`.*

---

## 5. Starting the Ollama LLM Backend

The LLM Validation layer assumes Ollama is running locally and serving the model defined in your `.env`.

In a **new terminal tab**, execute:
```bash
# Start the Ollama server and pull/run the specified model (e.g., llama3)
ollama run llama3:8b
```
Keep this process alive so FastAPI can ping `http://localhost:11434/api/generate` during the AI restructuring phase.

---

## 6. Running the Next.js Frontend (HITL)

With the backend and AI running, launch the Human-In-The-Loop Dashboard.

In a **new terminal tab**:
```bash
cd frontend
npm install
npm run dev
```
*The UI is now accessible at `http://localhost:3000`.*

---

## 7. End-to-End Integration Test 

To verify the platform end-to-end:

1. **Upload an Invoice:**
   - Go to `http://localhost:3000`
   - Upload a sample Arabic/English PDF Vendor Invoice.
2. **Watch the Celery Pipeline:**
   - Look at your Celery Worker terminal. You will see logs triggering:
     - `extract_text` (PaddleOCR / Poppler conversion)
     - `extract_financial_entities` (AraBERT NER Extraction)
     - `generate_json_validation` (Contacting Ollama LLM for structural formatting)
     - UAE VAT 5% Rule Math Check.
3. **Verify Dashboard Rendering:**
   - The UI will dynamically poll until the document state shifts from `PREPROCESSING` -> `HITL_REVIEW`.
   - Click **Review Issue**. You will see the original PDF on the left, and the OCR-extracted data on the right.
   - Any LLM hallucinations or anomalies (e.g., date formatted incorrectly) will be flagged with a Red Border (`Low Confidence`).
4. **Submit for Audit & ERP Export:**
   - Correct the invalid fields in the UI.
   - Click "Approve & Save". This updates the database and silently adds an immutable row into `DocumentAuditLog`.
   - The document is now `COMPLETED` and safely synced. If you configured Odoo/ERPNext credentials in your `.env`, you can now hit the POST `/documents/{id}/sync/odoo` endpoint to watch the background Celery ERP Sync task seamlessly execute with automated error-retries.
