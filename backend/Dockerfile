FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source into /app/backend/ so "from backend.xxx" imports work
COPY . ./backend/

# Create data dir for SQLite fallback
RUN mkdir -p /app/data

EXPOSE 8890

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8890"]
