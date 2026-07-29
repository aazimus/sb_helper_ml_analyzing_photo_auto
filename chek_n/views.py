# chek_n/views.py
import os
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CarPhotoRecord
from .ocr_service import recognize_plate

@csrf_exempt  # Только для теста! В продакшене так нельзя.
def webhook_simple(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Только POST'}, status=405)

    try:
        data = request.POST if request.POST else {}
        if not data and request.body:
            import json
            data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Неверный JSON'}, status=400)

    group_name = data.get('group_name')
    photo_url = data.get('photo_url')  # тут может быть и путь, и URL — это нормально

    if not group_name or not photo_url:
        return JsonResponse({'error': 'Нужны group_name и photo_url'}, status=400)

    record = CarPhotoRecord.objects.create(
        group_name=group_name,
        photo_path=photo_url,
        status='pending',
    )

    return JsonResponse({
        'id': record.id,
        'group_name': record.group_name,
        'photo_url': record.photo_path,
        'status': record.status,
    }, status=201)


@csrf_exempt
def finish_processing(request, record_id):
    try:
        record = CarPhotoRecord.objects.get(pk=record_id)
    except CarPhotoRecord.DoesNotExist:
        return JsonResponse({'error': 'Запись не найдена'}, status=404)

    url_or_path = record.photo_path

    # Если это локальный путь и файл реально существует — используем как есть
    if os.path.exists(url_or_path):
        local_path = url_or_path
    else:
        # Если это URL — пытаемся скачать во временную папку
        local_dir = 'temp_photos'
        os.makedirs(local_dir, exist_ok=True)
        filename = os.path.basename(url_or_path.replace('%20', ' '))
        local_path = os.path.join(local_dir, filename)

        try:
            r = requests.get(url_or_path, timeout=10)
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            record.status = 'error'
            record.plate_number = f'Не удалось скачать фото: {e}'
            record.save()
            return JsonResponse({
                'id': record.id,
                'status': record.status,
                'plate_number': record.plate_number,
            })

    plate = recognize_plate(local_path)

    if plate is None or str(plate).strip() == '':
        record.status = 'error'
        record.plate_number = 'Не удалось распознать номер'
    else:
        record.status = 'success'
        record.plate_number = plate

    record.save()

    return JsonResponse({
        'id': record.id,
        'status': record.status,
        'plate_number': record.plate_number,
    })