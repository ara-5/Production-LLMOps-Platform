FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY sdk /app/sdk
RUN pip install --no-cache-dir -e /app/sdk

COPY backend /app/backend
COPY demo_app /app/demo_app
COPY scripts /app/scripts
COPY seed /app/seed

WORKDIR /app/backend
ENV PYTHONPATH=/app:/app/backend
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
