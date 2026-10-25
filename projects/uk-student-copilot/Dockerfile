FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_MODE=live LLM_ENABLED=1 TELEMETRY_DB=/app/runtime/telemetry.sqlite3
WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r requirements.txt -r requirements-llm.txt
RUN useradd --create-home app && mkdir /app/runtime /home/app/.cache && chown app:app /app/runtime /home/app/.cache
COPY --chown=app:app . .
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--limit-concurrency", "8"]
