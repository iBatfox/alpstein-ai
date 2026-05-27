#!/bin/sh
# Alpstein AI — dev/test bootstrap (B2.8)
# Contract: docs/deployment/deployment-contract.md
# One-shot: Python dev seed → optional documented SQL (no migrations, no uvicorn).
# Refuses production-like ALPSTEIN_AI_ENVIRONMENT. Does not log secrets.

set -eu

log() {
  printf '%s\n' "$*" >&2
}

assert_dev_environment() {
  env="${ALPSTEIN_AI_ENVIRONMENT:-}"
  normalized=$(printf '%s' "$env" | tr '[:upper:]' '[:lower:]')
  case "$normalized" in
    development|dev|local|test) ;;
    *)
      log "ERROR: bootstrap refused — ALPSTEIN_AI_ENVIRONMENT must be development, dev, local, or test"
      log "ERROR: current value: ${env:-<unset>}"
      exit 1
      ;;
  esac
  log "bootstrap: environment allowed (${env})"
}

require_database_url() {
  if [ -z "${ALPSTEIN_AI_DATABASE_URL:-}" ]; then
    log "ERROR: ALPSTEIN_AI_DATABASE_URL is required"
    exit 1
  fi
}

run_python_seed() {
  log "bootstrap: running scripts/seed_dev_ai_configuration.py"
  if ! python /app/scripts/seed_dev_ai_configuration.py; then
    log "ERROR: dev AI configuration seed failed"
    exit 1
  fi
}

run_sql_bootstrap() {
  case "${RUN_SQL_BOOTSTRAP:-true}" in
    true|1|yes|TRUE|Yes) ;;
    *) log "bootstrap: RUN_SQL_BOOTSTRAP disabled — skipping SQL"; return 0 ;;
  esac

  if [ -z "${POSTGRES_PASSWORD:-}" ]; then
    log "ERROR: POSTGRES_PASSWORD is required for SQL bootstrap"
    exit 1
  fi

  host="${POSTGRES_HOST:-postgres}"
  port="${POSTGRES_PORT:-5432}"
  user="${POSTGRES_USER:-alpstein}"
  db="${POSTGRES_DB:-alpstein_ai}"

  export PGPASSWORD="${POSTGRES_PASSWORD}"

  for sql_file in \
    /app/scripts/demo_business_separation.sql \
    /app/scripts/update_alpstein_pre_sales_behavior.sql
  do
    log "bootstrap: applying $(basename "$sql_file")"
    if ! psql -h "$host" -p "$port" -U "$user" -d "$db" -v ON_ERROR_STOP=1 -f "$sql_file"; then
      log "ERROR: SQL bootstrap failed: $sql_file"
      exit 1
    fi
  done
}

assert_dev_environment
require_database_url
run_python_seed
run_sql_bootstrap
log "bootstrap: completed successfully"
exit 0
