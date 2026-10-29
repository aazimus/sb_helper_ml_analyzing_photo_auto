FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Системные зависимости (до pip install — нужны для psycopg2, Pillow)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        libgl1 \
        libglib2.0-0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 2. Зависимости Python
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# 3. Копируем весь проект
COPY . /app

# 4. Права на entrypoint
RUN chmod +x /app/entrypoint.sh

# Django-модули находятся в /app/backend
WORKDIR /app/backend

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "cheking_number_car.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
