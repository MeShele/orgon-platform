FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create "backend" symlink so "from backend.xxx" imports resolve to current dir
RUN ln -sf /app /app/backend

RUN mkdir -p /app/data

EXPOSE 8890

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8890"]
