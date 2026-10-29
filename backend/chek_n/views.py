import hmac
import json
import logging
import os

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .tasks import process_photo_task

logger = logging.getLogger(__name__)


def _verify_webhook_secret(request) -> bool:
    """
    Проверяет секретный ключ вебхука из заголовка X-Max-Bot-Api-Secret.
    Использует hmac.compare_digest для защиты от Timing Attacks.
    """
    secret = request.headers.get("X-Max-Bot-Api-Secret")
    # Берем секрет из settings (если задан там) или из переменных окружения
    expected = getattr(settings, "WEBHOOK_SECRET", None) or os.environ.get("WEBHOOK_SECRET", "my_secret_123")

    if not secret:
        return False

    return hmac.compare_digest(str(secret), str(expected))


def _parse_max_message(payload: dict) -> dict:
    """
    Встроенная версия парсера. Вытаскивает chat_id, текст и картинки (url + token).
    Не падает, если структура JSON немного отличается.
    """
    result = {
        "chat_id": None,
        "text": "",
        "images": []
    }

    if not isinstance(payload, dict):
        return result

    try:
        message = payload.get("message") or {}
        recipient = message.get("recipient") or {}
        result["chat_id"] = recipient.get("chat_id")

        body = message.get("body") or {}
        if "text" in body and body["text"] is not None:
            result["text"] = str(body["text"])

        attachments = body.get("attachments") or []
        for att in attachments:
            if isinstance(att, dict) and att.get("type") == "image":
                p = att.get("payload") or {}
                url = p.get("url")
                token = p.get("token")
                if url and token:
                    result["images"].append({"url": url, "token": token})
    except Exception as e:
        logger.warning(f"Ошибка при разборе структуры сообщения MAX: {e}")

    return result


@csrf_exempt
def webhook_max(request):
    """Основной обработчик вебхуков от MAX."""
    if request.method != "POST":
        return JsonResponse({"error": "Только POST"}, status=405)

    # Если на основном вебхуке тоже нужна проверка секрета — оставьте этот блок.
    # Если не нужна — закомментируйте следующие 4 строки.
    if not _verify_webhook_secret(request):
        logger.warning("Попытка доступа к webhook_max с неверным секретным ключом")
        return JsonResponse({"error": "Неверный секретный ключ"}, status=403)

    try:
        payload = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError as e:
        logger.error(f"Неверный JSON от MAX: {e}")
        return JsonResponse({"error": "Неверный JSON"}, status=400)

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
    """Тестовый эндпоинт для проверки заголовка безопасности вебхука."""
    if request.method != "POST":
        return JsonResponse({"error": "Только POST"}, status=405)

    if not _verify_webhook_secret(request):
        logger.warning("Проверка секрета в webhook_test: ключ не совпадает или отсутствует")
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