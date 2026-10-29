import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .tasks import process_photo_task

logger = logging.getLogger(__name__)


def _parse_max_message(payload):
    """
    Встроенная версия парсера. Вытаскивает chat_id, текст и картинки (url + token).
    Не падает, если структура JSON немного отличается.
    """
    result = {
        "chat_id": None,
        "text": "",
        "images": []
    }

    try:
        message = payload.get("message", {})
        recipient = message.get("recipient", {})
        result["chat_id"] = recipient.get("chat_id")

        body = message.get("body", {})
        if "text" in body:
            result["text"] = str(body["text"])

        attachments = body.get("attachments", [])
        for att in attachments:
            if att.get("type") == "image":
                p = att.get("payload", {})
                url = p.get("url")
                token = p.get("token")
                if url and token:
                    result["images"].append({"url": url, "token": token})
    except Exception:
        # Если JSON совсем битый — просто вернём пустой результат
        pass

    return result


@csrf_exempt
def webhook_max(request):
    if request.method != "POST":
        return JsonResponse({"error": "Только POST"}, status=405)

    try:
        payload = json.loads(request.body) if request.body else {}
    except Exception as e:
        logger.error(f"Неверный JSON от MAX: {e}")
        return JsonResponse({"error": "Неверный JSON"}, status=400)

    # Используем встроенную функцию, никакого импорта из parsers
    parsed = _parse_max_message(payload)

    chat_id = parsed["chat_id"]
    text = parsed["text"]
    images = parsed["images"]

    if chat_id is None:
        logger.warning("Не удалось извлечь chat_id из сообщения MAX")
        return JsonResponse({"error": "Не найден chat_id"}, status=400)

    if not images:
        logger.info(f"Сообщение от chat_id={chat_id} без картинок. Текст: {text[:50]}")
        return JsonResponse({
            "status": "ok",
            "message": "Сообщение получено, картинок нет",
            "chat_id": chat_id,
        }, status=200)

    for img in images:
        process_photo_task.delay(
            url=img["url"],
            token=img["token"],
            chat_id=str(chat_id),
            source="max"
        )
        logger.info(f"Задача Celery поставлена: chat_id={chat_id}, url={img['url'][:60]}...")

    return JsonResponse({
        "status": "accepted",
        "message": f"Принято {len(images)} изображений для обработки",
        "chat_id": chat_id,
        "images_count": len(images),
    }, status=202)


@csrf_exempt
def webhook_test(request):
    if request.method != "POST":
        return JsonResponse({"error": "Только POST"}, status=405)

    secret = request.headers.get("X-Max-Bot-Api-Secret")
    logger.info(f"Проверка секрета: пришёл={secret}")

    expected = os.environ.get("WEBHOOK_SECRET", "my_secret_123")`r`n    if secret != expected:
        logger.warning("Секретный ключ не совпадает!")
        return JsonResponse({
            "status": "error",
            "secret_check": "failed",
            "message": "Неверный секретный ключ",
        }, status=403)

    logger.info("Секретный ключ верный. Тест прошёл успешно.")
    return JsonResponse({
        "status": "ok",
        "secret_check": "passed",
        "message": "Тест прошёл успешно",
    }, status=200)

