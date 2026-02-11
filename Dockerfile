FROM python:3.11-slim

# Prevenir que Python escriba archivos .pyc y asegurar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema
# Se añaden librerías para: psycopg2, Pillow y WeasyPrint
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    # Dependencias específicas para WeasyPrint (PDF)
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
RUN pip install --upgrade pip
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . /app/

# Dar permisos al script de inicio (si usas uno) o definir el comando directo
EXPOSE 8000

# Usar Gunicorn para producción en lugar de runserver
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application", "./start.sh"], 