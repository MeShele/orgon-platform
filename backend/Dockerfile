FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Symlink so "from backend.xxx" imports resolve
RUN ln -sf /app /app/backend

# Default config + data dir
RUN mkdir -p /app/config /app/data
COPY config_default.yaml /app/config/orgon.yaml

EXPOSE 8890

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8890"]
