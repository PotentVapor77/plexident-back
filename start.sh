#!/bin/bash

# Salir inmediatamente si un comando falla
set -e

echo "==> Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

echo "==> Recolectando archivos estáticos..."
# Esto es necesario si usas librerías como Whitenoise o si subes a S3
python manage.py collectstatic --noinput

echo "==> Iniciando Gunicorn..."
# config.wsgi debe coincidir con el nombre de tu carpeta de proyecto 
python -m gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3