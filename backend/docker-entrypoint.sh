#!/bin/sh
# Alpstein AI backend — migrate-then-serve (B2.5)
# Contract: docs/deployment/deployment-contract.md
# Lifecycle: optional postgres wait → alembic upgrade head → exec uvicorn
# Does not log secrets. Exits non-zero on migration failure (uvicorn never starts).

set -eu

log() {
  printf '%s\n' "$*" >&2
}

wait_for_postgres() {
  case "${WAIT_FOR_POSTGRES:-true}" in
    true|1|yes|TRUE|Yes) ;;
    *) return 0 ;;
  esac

  host="${POSTGRES_HOST:-postgres}"
  port="${POSTGRES_PORT:-5432}"
  user="${POSTGRES_USER:-alpstein}"
  max_attempts="${POSTGRES_WAIT_MAX_ATTEMPTS:-30}"
  delay_seconds="${POSTGRES_WAIT_DELAY_SECONDS:-2}"

  attempt=1
  while [ "$attempt" -le "$max_attempts" ]; do
    if pg_isready -h "$host" -p "$port" -U "$user" -q; then
      log "postgres ready (${host}:${port})"
      return 0
    fi
    log "waiting for postgres (${attempt}/${max_attempts}) at ${host}:${port}..."
    attempt=$((attempt + 1))
    sleep "$delay_seconds"
  done

  log "ERROR: postgres not ready after ${max_attempts} attempts (${host}:${port})"
  exit 1
}

run_migrations() {
  if [ -z "${ALPSTEIN_AI_DATABASE_URL:-}" ]; then
    log "ERROR: ALPSTEIN_AI_DATABASE_URL is required for alembic upgrade head"
    exit 1
  fi

  log "running alembic upgrade head"
  if ! alembic upgrade head; then
    log "ERROR: alembic upgrade head failed — uvicorn will not start"
    exit 1
  fi
  log "alembic upgrade head completed"
}

start_uvicorn() {
  log "starting uvicorn on 0.0.0.0:8000"
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000
}

wait_for_postgres
run_migrations
start_uvicorn
