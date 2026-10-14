# chek_n/views.py
import os
import json
import logging
import shutil
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .tasks import process_photo_task


from django.http import HttpResponse

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook_simple(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Только POST'}, status=405)

    try:
        data = json.loads(request.body) if request.body else {}
    except Exception as e:
        logger.error(f"Неверный JSON: {e}")
        return JsonResponse({'error': 'Неверный JSON'}, status=400)

    file_info = data.get('file') or {}
    photo_path = file_info.get('path') or data.get('photo_url') or data.get('path')
    group_name = (
        data.get('group_name')
        or data.get('chat_id')
        or data.get('user_id')
        or 'default-group'
    )

    if not photo_path:
        return JsonResponse({'error': 'Не передан путь к файлу'}, status=400)

    src = Path(photo_path)
    if not src.exists():
        logger.error(f"Файл не найден: {photo_path}")
        return JsonResponse({'error': 'Файл не найден на диске'}, status=400)

    incoming_dir = Path(settings.MEDIA_ROOT) / 'incoming'
    incoming_dir.mkdir(parents=True, exist_ok=True)

    dest = incoming_dir / src.name
    try:
        shutil.copy2(src, dest)
    except Exception as e:
        logger.exception(f"Не удалось скопировать файл: {e}")
        return JsonResponse({'error': 'Ошибка копирования файла'}, status=500)

    process_photo_task.delay(str(dest), str(group_name), str(photo_path))

    logger.info(f"Задача поставлена: {dest.name} | группа={group_name}")

    return JsonResponse({
        'status': 'accepted',
        'message': 'Фото принято в обработку',
        'group_name': group_name,
        'file': src.name,
    }, status=202)


@csrf_exempt
def finish_processing(request, record_id):
    return JsonResponse({
        'message': 'Больше не используется. Обработка идёт через Celery.',
    })
@csrf_exempt
def webhook_test(request):
    if request.method != "POST":
        return JsonResponse({'error': 'Только POST'}, status=405)

    print("--- Пришёл вебхук от MAX (ТЕСТ) ---")

    # Безопасное получение заголовков
    headers_dict = dict(request.headers)
    print("Headers:", headers_dict)

    body_text = ""
    try:
        body_text = request.body.decode('utf-8', errors='ignore')
        print("Body (raw):", body_text)
    except Exception as e:
        print(f"⚠️ Ошибка декодирования body: {e}")

    secret = request.headers.get('X-Max-Bot-Api-Secret')
    if secret != 'my_secret_123':
        print("⚠️ Секретный ключ не совпадает! Пришёл:", secret)
        # Для теста всё равно отдадим 200, чтобы MAX не помечал вебхук как сломанный
        return JsonResponse({
            'status': 'received',
            'secret_check': 'failed',
            'message': 'Запрос получен, но секрет не совпадает'
        }, status=200)
    else:
        print("✅ Секретный ключ верный.")

    return JsonResponse({
        'status': 'ok',
        'secret_check': 'passed',
        'message': 'Тест прошёл успешно'
    }, status=200)