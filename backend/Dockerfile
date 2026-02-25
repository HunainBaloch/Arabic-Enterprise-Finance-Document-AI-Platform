FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-ara \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install ONLY lightweight API/DB/web packages (no torch, no paddleocr, no transformers)
# Heavy AI packages are pre-downloaded and bind-mounted from the host.
COPY requirements-api.txt /tmp/requirements-api.txt
RUN pip install --upgrade pip --quiet && \
    pip install --quiet -r /tmp/requirements-api.txt

# App code
COPY . /app/

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
