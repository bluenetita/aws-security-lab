FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BLUEGUARD_MODE=demo \
    BLUEGUARD_ALERTS_FILE=/app/demo/alerts.json
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && groupadd --gid 10001 blueguard \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin blueguard
COPY app /app/app
COPY demo /app/demo
USER 10001:10001
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-server-header"]
