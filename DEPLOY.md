# Деплой — инструкция по запуску

## Требования

- Docker >= 24
- Docker Compose >= 2.x
- ML-модели (см. ниже)

---

## 1. Подготовка ML-моделей (обязательно перед сборкой!)

Модели не хранятся в репозитории. Перед `docker-compose up` убедитесь что они на месте:

```
backend/models/DETECT.pt      ← YOLO-модель детекции номеров
backend/models/CRNN.pth       ← CRNN-модель распознавания
backend/data/charset.json     ← словарь символов
```

## 2. Настройка окружения

```bash
cp .env.example .env
# Отредактируйте .env: задайте SECRET_KEY и DB_PASSWORD
```

## 3. Запуск

```bash
docker-compose up --build
```

Сервисы:
| Сервис | URL |
|--------|-----|
| Django API | http://localhost:8000 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

## 4. Архитектура контейнеров

```
backend       — Django + Gunicorn (без torch/ML)
worker        — Celery + torch + YOLO + CRNN (ML-обработка)
db            — PostgreSQL 15
redis         — Redis 7
```

> **Примечание:** `backend` и `worker` собираются из разных Dockerfile.
> `backend` — лёгкий образ (~500 МБ).
> `worker` — тяжёлый образ с torch (~5–8 ГБ, долгая сборка).
