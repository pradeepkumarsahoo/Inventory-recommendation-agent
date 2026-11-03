FROM python:3.12-slim

WORKDIR /app

# Install deps first to keep layer cache stable across code changes.
COPY ai-agents/requirements.txt /app/ai-agents/requirements.txt
RUN pip install --no-cache-dir -r /app/ai-agents/requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn[standard]

COPY ai-agents /app/ai-agents
COPY ai-guardrails /app/ai-guardrails

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/ai-agents \
    RETAIL_SAMPLE_DATA_DIR=/app/data

EXPOSE 7071

CMD ["python", "/app/ai-agents/service.py"]
