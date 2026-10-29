import os
import json
from pathlib import Path
from django.test import TestCase, Client
from django.urls import reverse
from celery import current_app
from unittest.mock import patch

from chek_n.models import CarPhotoRecord
from chek_n.tasks import process_photo_task

# ВАЖНО: этот путь строится от корня проекта (где лежит manage.py)
# Мы поднимаемся от __file__ на 2 уровня вверх: backend/tests -> backend
BASE_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"

class CarPhotoRecordTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse('webhook_max')
        current_app.control.purge()

    @patch('chek_n.tasks.recognize_plate')
    def test_webhook_accepts_max_payload(self, mock_ocr):
        mock_ocr.return_value = ("A001AA777", "/tmp/crop.jpg")

        payload = {
            "message": {
                "recipient": {"chat_id": 987654321},
                "body": {
                    "text": "Проверь номер",
                    "attachments": [
                        {
                            "type": "image",
                            "payload": {
                                "url": "https://via.placeholder.com/300.png",
                                "token": "fake-token-123"
                            }
                        }
                    ]
                }
            }
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_MAX_BOT_API_SECRET='my_secret_123'
        )

        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertEqual(data['status'], 'accepted')
        self.assertTrue(CarPhotoRecord.objects.exists())

    def test_celery_task_processes_real_file(self):
        if not FIXTURES_DIR.exists():
            contents = [p.name for p in Path(BASE_DIR).iterdir()] if Path(BASE_DIR).is_dir() else []
            self.skipTest(f"Папка {FIXTURES_DIR} не найдена. Видимые папки в BASE_DIR: {contents}")

        files = list(FIXTURES_DIR.glob("*.jpg")) + list(FIXTURES_DIR.glob("*.png"))
        if not files:
            contents = [p.name for p in FIXTURES_DIR.iterdir()] if FIXTURES_DIR.is_dir() else []
            self.skipTest(f"В папке {FIXTURES_DIR} нет картинок (.jpg/.png). Видимые файлы: {contents}")

        test_file = files[0]

        with open(test_file, "rb") as f:
            real_image_bytes = f.read()

        mock_resp = type('Response', (object,), {
            'status_code': 200,
            'content': real_image_bytes
        })

        with patch('chek_n.tasks.requests.get', return_value=mock_resp):
            result = process_photo_task(
                url="http://fake.url/test.jpg",
                token="secret-token",
                chat_id="999888777",
                group_name="Real File Test Group",
                source="max"
            )

        self.assertEqual(result['status'], 'success')

        record = CarPhotoRecord.objects.last()
        self.assertIsNotNone(record)
        self.assertIsNotNone(record.plate_number)
        self.assertEqual(record.status, 'success')
        self.assertTrue(len(record.plate_number.strip()) > 0)

    def test_webhook_rejects_without_secret(self):
        payload = {"message": {"recipient": {"chat_id": 123}, "body": {"text": "Hi", "attachments": []}}}
        response = self.client.post(self.webhook_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_webhook_rejects_no_images(self):
        payload = {"message": {"recipient": {"chat_id": 456}, "body": {"text": "Просто текст"}}}
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_MAX_BOT_API_SECRET='my_secret_123'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['message'], 'Сообщение получено, картинок нет')
