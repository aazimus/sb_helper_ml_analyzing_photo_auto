#!/bin/bash

echo "=== Начинаем деплой ==="

# 1. Получаем свежий код из ветки production
git fetch origin
git checkout production
git pull origin production

# 2. Пересобираем и перезапускаем Docker-контейнеры
echo "=== Пересборка Docker контейнеров ==="
docker compose down
docker compose up -d --build

# 3. Применяем миграции базы данных
echo "=== Применение миграций Django ==="
docker exec -it car_number_check_backend python manage.py migrate --noinput

echo "=== Деплой успешно завершен! ==="
