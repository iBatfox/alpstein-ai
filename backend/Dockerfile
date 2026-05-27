# Alpstein AI backend — application image (B2.3+)
# Contract: docs/deployment/deployment-contract.md
# Build context: backend/ (directory containing this Dockerfile)
#
#   docker build -f Dockerfile -t alpstein-ai-backend:local .
#
# Migrations run at container start via docker-entrypoint.sh (B2.5), not at image build.
# Wired in root docker-compose.yml as service `backend` (B2.6).

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 alpstein \
    && useradd --uid 1000 --gid alpstein --create-home --shell /usr/sbin/nologin alpstein

COPY requirements-prod.txt .
RUN pip install -r requirements-prod.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
COPY docker-bootstrap.sh /app/docker-bootstrap.sh

RUN chmod +x /app/docker-entrypoint.sh /app/docker-bootstrap.sh \
    && chown -R alpstein:alpstein /app

USER alpstein

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
