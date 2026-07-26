# syntax=docker/dockerfile:1.6
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends wget && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --no-create-home app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
COPY . .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e .
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:8080/healthz || exit 1
CMD ["uvicorn", "reconciliation.app:app", "--host", "0.0.0.0", "--port", "8080"]