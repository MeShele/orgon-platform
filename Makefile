.PHONY: install run dev test clean migrate

install:
	pip install -r requirements.txt

run:
	uvicorn backend.main:app --host 0.0.0.0 --port 8890

dev:
	uvicorn backend.main:app --host 0.0.0.0 --port 8890 --reload

test:
	python -m pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

migrate:
	python -c "from backend.database.migrations import run_migrations; run_migrations()"
