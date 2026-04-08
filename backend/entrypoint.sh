#!/bin/sh
set -eu

ROLE="${APP_ROLE:-web}"

echo "[startup] app_role=${ROLE}"

if [ "$ROLE" = "scheduler" ]; then
  echo "[startup] iniciando processo dedicado do scheduler"
  exec python run_scheduler.py
fi

echo "[startup] processo web selecionado; scheduler desabilitado neste processo"
exec gunicorn --bind 0.0.0.0:${PORT} \
  --workers ${WEB_CONCURRENCY:-1} \
  --threads ${GUNICORN_THREADS:-4} \
  --worker-class gthread \
  --timeout ${GUNICORN_TIMEOUT:-120} \
  app:app
