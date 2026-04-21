#!/usr/bin/env sh
set -eu

echo "==> Running scaffold test suite in Docker"

if [ ! -f "docker-compose.yml" ]; then
  echo "ERROR: docker-compose.yml not found. Run this script from repo/ root."
  exit 1
fi

if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    echo "==> .env not found, creating from .env.example"
    cp .env.example .env
  else
    echo "ERROR: .env not found and .env.example is missing."
    exit 1
  fi
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is required but was not found."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: Docker Compose plugin is required but not available."
  exit 1
fi

if [ ! -d "unit_tests" ]; then
  echo "ERROR: unit_tests/ directory is missing."
  exit 1
fi

if [ ! -d "API_tests" ]; then
  echo "ERROR: API_tests/ directory is missing."
  exit 1
fi

TEARDOWN="${TEARDOWN:-0}"

cleanup() {
  if [ "${TEARDOWN}" = "1" ]; then
    echo "==> Tearing down Docker services"
    docker compose down -v
  else
    echo "==> Leaving Docker services running (set TEARDOWN=1 to auto-stop)"
  fi
}

trap cleanup EXIT

echo "==> Building and starting services"
docker compose up -d --build

echo "==> Waiting for database health"
DB_CONTAINER="offline_retail_db"
MAX_WAIT=60
WAITED=0
SLEEP_STEP=2

while [ "${WAITED}" -lt "${MAX_WAIT}" ]; do
  STATUS="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' "${DB_CONTAINER}" 2>/dev/null || true)"
  if [ "${STATUS}" = "healthy" ]; then
    echo "==> Database is healthy"
    break
  fi
  sleep "${SLEEP_STEP}"
  WAITED=$((WAITED + SLEEP_STEP))
done

if [ "${WAITED}" -ge "${MAX_WAIT}" ]; then
  echo "ERROR: Database did not become healthy within ${MAX_WAIT}s"
  docker compose ps
  docker compose logs db || true
  exit 1
fi

echo "==> Running unit tests in api container"
docker compose exec -T api sh -c "PYTHONPATH=/app pytest -q unit_tests"

echo "==> Running API tests in api container"
docker compose exec -T api sh -c "PYTHONPATH=/app pytest -q API_tests"

echo "✅ All scaffold tests passed in Docker"
