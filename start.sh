#!/bin/bash
set -e

echo "==> Aplicando migraciones..."
python manage.py migrate --noinput

echo "==> Recolectando estáticos..."
python manage.py collectstatic --noinput

echo "==> Iniciando Gunicorn..."
# IMPORTANTE: Usar 'python -m gunicorn'
exec python -m gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3