# Manual Configuration Guide: PostgreSQL 18 Integration

This guide provides step-by-step instructions to manually configure and run the **Arabic Enterprise Finance Document AI Platform** using a local installation of **PostgreSQL 18**.

---

## 1. Prerequisites

- **PostgreSQL 18** installed on your host machine.
- **Python 3.10+** (Recommend 3.12 for best compatibility with current dependencies).
- **Redis** server running locally (for Celery).
- **Poppler** and **Tesseract/PaddleOCR** dependencies as outlined in the `DEVELOPER_GUIDE.md`.

---

## 2. Database Preparation

Open your PostgreSQL command line (`psql`) or a GUI tool like pgAdmin / DBeaver and execute the following commands to set up the dedicated database and user:

```sql
-- 1. Create the application user
CREATE USER idp_admin WITH PASSWORD 'admin';

-- 2. Create the application database
CREATE DATABASE idp_db OWNER idp_admin;

-- 3. Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE idp_db TO idp_admin;

-- 4. Enable UUID extension (Required for our primary keys)
\c idp_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

---

## 3. Environment Configuration (`.env`)

Update your `.env` file in the project root (and ensure a copy exists in the `backend/` folder) to point to your manual PostgreSQL 18 instance.

**File: `.env`**
```ini
# Database Configuration
# If your local Postgres is running on the default port 5432, use that.
# If you have multiple versions and 18 is on 5434, update accordingly.
POSTGRES_USER=idp_admin
POSTGRES_PASSWORD=admin
POSTGRES_DB=idp_db
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

# Redis Configuration
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# FastAPI Configuration
SECRET_KEY=4a76c560dc27879636d15d9d5a92f568f4ef1bfdddf73e337292a3964922328
API_V1_STR=/api/v1
PROJECT_NAME="Arabic Enterprise Finance IDP Platform"

# AI Configuration
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3:8b
```

---

## 4. Backend Setup & Migrations

Navigate to the `backend` directory and follow these steps to initialize the schema:

### 4.1 Install Dependencies
Make sure your virtual environment is active.
```bash
pip install -r requirements.txt
```

### 4.2 Run Database Migrations
This will create the `user`, `document`, and `documentauditlog` tables in your local PostgreSQL 18 instance.
```bash
alembic upgrade head
```

### 4.3 Create a Manual Test User (Optional)
If you need to seed a user to bypass the login check initially:
```bash
# Start a python shell
python
>>> from app.db.session import SessionLocal
>>> from app.models.user import User
>>> from app.core.security import get_password_hash
>>> import asyncio
>>> async def create_user():
...     async with SessionLocal() as db:
...         user = User(email="admin@example.com", hashed_password=get_password_hash("admin"), role="admin")
...         db.add(user)
...         await db.commit()
>>> asyncio.run(create_user())
```

---

## 5. Running the Application

With the database configured manually:

1. **Start the API:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Start the Celery Worker (In a separate terminal):**
   ```bash
   celery -A app.core.celery_app worker -n worker@%h -l info -P solo
   ```

3. **Start the Frontend:**
   ```bash
   cd ../frontend
   npm run dev
   ```

---

## Troubleshooting Connectivity

- **`socket.gaierror` / `Connection Refused`**: Double-check that `POSTGRES_HOST` is set to `127.0.0.1` rather than `db` (which is only for Docker networking).
- **`Password authentication failed`**: Ensure the credentials in your `.env` EXACTLY match what you set in Step 2.
- **PostgreSQL 18 Features**: Our SQLAlchemy/Alembic setup uses standard SQL/PostgreSQL types and is fully compatible with version 18's architectural improvements.
