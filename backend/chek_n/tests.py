import json
import sys
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, override_settings
from chek_n.models import CarPhotoRecord, ChatGroup
from chek_n.tasks import process_photo_task

WEBHOOK_PAYLOAD_1_PHOTO = {
    "message": {
        "recipient": {"chat_type": "chat", "chat_id": -79397419554856},
        "timestamp": 1792945647384,
        "body": {
            "mid": "mid.ffffb7c9d902e7d801a173e36f180a84",
            "seq": 117502485946960516,
            "text": "",
            "attachments": [
                {
                    "payload": {
                        "photo_id": 47628366120,
                        "token": "ouqxt1KuEBDYI25VuOHlIBz9FoXJd/Pc07JeJWrKj0RWgpTi8q1N6j3cjBMkbXUiaCKs/jUuwlRDR1k7Lw/IcZ9l5aENQV63GySTXnXEcd0=",
                        "url": "https://i.oneme.ru/i?r=BTGWjORktRiuuNetttkJiSt5jBsd8iKpbRc4HJXsqVeDX2Zw5IyjmFCjDHMXD0Bdtn0"
                    },
                    "type": "image"
                }
            ]
        },
        "sender": {
            "user_id": 206251816,
            "first_name": "Артур",
            "is_bot": False,
            "last_name": "Беккер",
            "last_activity_time": 1792945648000,
            "name": "Артур Беккер"
        }
    },
    "timestamp": 1792945647384,
    "update_type": "message_created"
}

WEBHOOK_PAYLOAD_4_PHOTOS = {
    "message": {
        "recipient": {"chat_type": "chat", "chat_id": -79397419554856},
        "timestamp": 1792945693163,
        "body": {
            "mid": "mid.ffffb7c9d902e7d801a173e421eb151e",
            "seq": 117502488947135774,
            "text": "",
            "attachments": [
                {
                    "payload": {
                        "photo_id": 47628366120,
                        "token": "k+vM7fQ7KAoXXZaJPJOechUywYEN7ZtCH28q0Zc2IyBsDzxSKskKIjLS2WMKIIbqM9rfYbWLLigLX+nem2hbBZVrJ/mirq+kkP3QpOvKPe4=",
                        "url": "https://i.oneme.ru/i?r=BTGWjORktRiuuNetttkJiSt5jBsd8iKpbRc4HJXsqVeDX2Zw5IyjmFCjDHMXD0Bdtn0"
                    },
                    "type": "image"
                },
                {
                    "payload": {
                        "photo_id": 47628498984,
                        "token": "UzrzJ5HV2Qm9xztbnqp675DkuMGtS7tnZSNXIbPghBykRbK8iYgs10Z63QQO8bjed0Xklau+DNPuHGasrXY0sGm1XxXS/TLa2HLM5qcgq9A=",
                        "url": "https://i.oneme.ru/i?r=BTGWjORktRiuuNetttkJiSt57Kixq3ZeN37Ib76kYMqO_WZw5IyjmFCjDHMXD0Bdtn0"
                    },
                    "type": "image"
                },
                {
                    "payload": {
                        "photo_id": 47628498728,
                        "token": "HKAnHjlcxK58M9VbHcMk3FJ+d0HJHyYXH5yWfHi7iL4cVtlMcWTysEvGnfPfFm1nPFNF3x5ZTF1/YovhJixAJ4nqXL89wAAGkI+Na+gUO9k=",
                        "url": "https://i.oneme.ru/i?r=BTGWjORktRiuuNetttkJiSt5XoeSMivMrk_d4fLP8LkYXGZw5IyjmFCjDHMXD0Bdtn0"
                    },
                    "type": "image"
                },
                {
                    "payload": {
                        "photo_id": 47628499240,
                        "token": "tUjM0cIcwE2+V8CErET/NribZPwgZQW3Ag+M/fGb5v9FwgTelf64rfPS2ao3Z7OUR5bcS/mogaisu8dBAB0m4Qt01utgirgmUOYvu+FbG1I=",
                        "url": "https://i.oneme.ru/i?r=BTGWjORktRiuuNetttkJiSt5X_PjLWhtGUdwV3mT8CytB2Zw5IyjmFCjDHMXD0Bdtn0"
                    },
                    "type": "image"
                }
            ]
        },
        "sender": {
            "user_id": 206251816,
            "first_name": "Артур",
            "is_bot": False,
            "last_name": "Беккер",
            "last_activity_time": 1792945694000,
            "name": "Артур Беккер"
        }
    },
    "timestamp": 1792945693163,
    "update_type": "message_created"
}

EXPECTED_PLATES = ["А111АА777", "В222ВВ777", "Е333ЕЕ777", "К444КК777"]


@override_settings(WEBHOOK_SECRET="my_secret_123")
class CarPhotoRecordTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.webhook_url = "/api/webhook/max/"
        self.headers = {"HTTP_X_MAX_BOT_API_SECRET": "my_secret_123"}
        # Очищаем таблицы перед каждым тестом для полной изоляции
        ChatGroup.objects.all().delete()
        CarPhotoRecord.objects.all().delete()

    def test_webhook_rejects_invalid_secret(self):
        resp = self.client.post(
            self.webhook_url,
            data=json.dumps(WEBHOOK_PAYLOAD_1_PHOTO),
            content_type="application/json",
            HTTP_X_MAX_BOT_API_SECRET="wrong_secret"
        )
        self.assertEqual(resp.status_code, 403)

    @patch.object(process_photo_task, "delay")
    def test_webhook_accepts_max_payload(self, mock_delay):
        resp = self.client.post(
            self.webhook_url,
            data=json.dumps(WEBHOOK_PAYLOAD_4_PHOTOS),
            content_type="application/json",
            **self.headers
        )
        self.assertEqual(resp.status_code, 202)
        data = resp.json()
        self.assertEqual(data["images_count"], 4)
        self.assertEqual(data["chat_id"], -79397419554856)
        self.assertEqual(mock_delay.call_count, 4)

    @patch("requests.get")
    def test_celery_task_processes_max_photos(self, mock_get):
        chat_info_response = MagicMock()
        chat_info_response.status_code = 200
        chat_info_response.json.return_value = {"title": "Тестовая Автомойка"}

        image_response = MagicMock()
        image_response.status_code = 200
        image_response.content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        # Безопасное разделение моков по домену или пути
        def side_effect(url, *args, **kwargs):
            if "platform-api.max.ru" in str(url):
                return chat_info_response
            return image_response

        mock_get.side_effect = side_effect

        mock_ocr_module = MagicMock()
        mock_ocr_module.recognize_plate.side_effect = [(plate, None) for plate in EXPECTED_PLATES]

        with patch.dict(sys.modules, {
            "chek_n.ocr_service": mock_ocr_module,
            "backend.chek_n.ocr_service": mock_ocr_module,
        }):
            attachments = WEBHOOK_PAYLOAD_4_PHOTOS["message"]["body"]["attachments"]
            for att in attachments:
                p = att["payload"]
                process_photo_task(
                    url=p["url"],
                    token=p["token"],
                    chat_id="-79397419554856",
                    source="max"
                )

        group = ChatGroup.objects.get(chat_id="-79397419554856")
        self.assertEqual(group.name, "Тестовая Автомойка")
        self.assertTrue(group.is_active)

        records = CarPhotoRecord.objects.filter(status="success").order_by("id")
        self.assertEqual(records.count(), 4)
        saved_plates = [r.plate_number for r in records]
        self.assertEqual(saved_plates, EXPECTED_PLATES)

        group = ChatGroup.objects.get(chat_id="-79397419554856")
        self.assertEqual(group.name, "Тестовая Автомойка")
        self.assertTrue(group.is_active)

        records = CarPhotoRecord.objects.filter(status="success").order_by("id")
        self.assertEqual(records.count(), 4)
        saved_plates = [r.plate_number for r in records]
        self.assertEqual(saved_plates, EXPECTED_PLATES)

    @patch("requests.get")
    def test_chat_group_blocking(self, mock_get):
        ChatGroup.objects.create(
            chat_id="-79397419554856",
            name="Заблокированный чат",
            is_active=False
        )

        att = WEBHOOK_PAYLOAD_1_PHOTO["message"]["body"]["attachments"][0]["payload"]
        res = process_photo_task(
            url=att["url"],
            token=att["token"],
            chat_id="-79397419554856",
            source="max"
        )

        self.assertEqual(res.get("status"), "blocked")
        self.assertEqual(CarPhotoRecord.objects.count(), 0)