markdown
# car_number_cheking

Сервис распознавания автомобильных номеров: YOLO для детекции, CRNN для OCR, Django 6.0.7 как бэкенд.

## Структура

- `chek_n/` — Django-приложение (модели, сериализаторы, views, ocr_service.py)
- `training/` — скрипты обучения и подготовки данных (train.py, charset.py, data.yaml)
- `tests/` — тесты пайплайна и загрузки весов
- `ml_requirements.txt` — зависимости ML-части

## Важное

- **Веса моделей** (`yolov8n.pt`, `CRNN.pth`) хранятся **локально** в папке `training/` и **не коммитятся** (см. `.gitignore`).
- **Датасеты и CSV** также хранятся локально. Скрипты для их генерации: `prepare_nomeroff.py`, `created_csv_crnn.py`.
- **Charset** (22 символа) определён в `training/charset.json` и `training/charset.py`.

## Установка и запуск

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r ml_requirements.txt
python manage.py migrate
python manage.py runserver
Обучение
bash
cd training
python train.py
python train_crnn_val.py
Тестирование пайплайна
bash
python test_pipeline.py
text

---

Что тебе сейчас ближе:
- ✅ сделать бэкап и выдохнуть,
- ✅ проверить `test_pipeline.py`,
- ✅ оформить `README.md`,
- или просто сказать «ура, Git починил» и закрыть тему? 😊

Скажи, что выбираешь — и я помогу именно с этим шагом.
