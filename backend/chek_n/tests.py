from django.test import TestCase, Client
from django.urls import reverse
from .models import CarPhotoRecord
from unittest.mock import patch

class CarPhotoRecordTests(TestCase):
    def setUp(self):
        """Подготавливаем данные перед каждым тестом"""
        self.client = Client()
        self.webhook_url = reverse('webhook_simple')  # проверь, что имя совпадает с urls.py
        self.finish_url_template = '/api/finish/{}/'

    @patch('chek_n.views.recognize_plate')
    def test_webhook_creates_record_with_pending_status(self, mock_ocr):
        """Тест 1: Webhook создаёт запись со статусом pending"""
        mock_ocr.return_value = "A001AA777"  # заглушка, чтобы тест не зависел от сети
        payload = {
            "group_name": "Тестовая группа",
            "photo_url": "http://example.com/test.jpg"
        }

        response = self.client.post(self.webhook_url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(CarPhotoRecord.objects.exists())
        record = CarPhotoRecord.objects.first()
        self.assertEqual(record.status, CarPhotoRecord.STATUS_PENDING)
        self.assertEqual(record.group_name, "Тестовая группа")

    @patch('chek_n.views.recognize_plate')
    def test_finish_returns_404_for_nonexistent_record(self, mock_ocr):
        """Тест 4: Finish возвращает 404, если запись не найдена"""
        nonexistent_id = 99999
        finish_url = self.finish_url_template.format(nonexistent_id)
        response = self.client.post(finish_url)

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('error', data)

    @patch('chek_n.views.recognize_plate')
    def test_finish_sets_done_and_saves_plate_when_ocr_succeeds(self, mock_ocr):
        """Тест 2: Finish ставит done и сохраняет номер, если OCR что-то вернул"""
        # 1. Сначала создадим запись
        create_payload = {
            "group_name": "Группа 2",
            "photo_url": "http://example.com/car.jpg"
        }
        create_resp = self.client.post(self.webhook_url, data=create_payload, content_type='application/json')
        record_id = create_resp.json()['id']

        # 2. Подменяем результат OCR на реальный номер
        mock_ocr.return_value = "В123ВВ799"

        # 3. Вызываем finish
        finish_url = self.finish_url_template.format(record_id)
        response = self.client.post(finish_url)

        self.assertEqual(response.status_code, 200)
        record = CarPhotoRecord.objects.get(pk=record_id)
        self.assertEqual(record.status, CarPhotoRecord.STATUS_DONE)
        self.assertEqual(record.plate_number, "В123ВВ799")

    @patch('chek_n.views.recognize_plate')
    def test_finish_sets_error_when_ocr_returns_none(self, mock_ocr):
        """Тест 3: Finish ставит error, если OCR ничего не нашёл (None)"""
        # 1. Создаём запись
        create_payload = {
            "group_name": "Группа 3",
            "photo_url": "http://example.com/bad.jpg"
        }
        create_resp = self.client.post(self.webhook_url, data=create_payload, content_type='application/json')
        record_id = create_resp.json()['id']

        # 2. Говорим OCR: «ничего не распозналось»
        mock_ocr.return_value = None

        # 3. Вызываем finish
        finish_url = self.finish_url_template.format(record_id)
        response = self.client.post(finish_url)

        self.assertEqual(response.status_code, 200)  # API всё равно должен ответить 200, даже если результат плохой
        record = CarPhotoRecord.objects.get(pk=record_id)
        self.assertEqual(record.status, CarPhotoRecord.STATUS_ERROR)
        self.assertEqual(record.plate_number, "Не удалось распознать номер")