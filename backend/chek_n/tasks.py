import os
import logging
import requests
from celery import shared_task
from django.core.files import File

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def process_photo_task(
    self,
    local_path: str = None,
    group_name: str = "default-group",
    original_photo_path: str = "",
    url: str = None,
    token: str = None,
    chat_id: str = None,
    source: str = "local"
):
    """
    Универсальная задача:
    - source='local': работает как раньше
    - source='max': скачивает картинку через Authorization: Bearer {token} (официальный способ MAX 2026)
    """
    from .ocr_service import recognize_plate
    from .models import CarPhotoRecord

    temp_file_path = None

    try:
        # --- ШАГ 1: Получить файл на диск (официальный способ MAX) ---
        if source == "max":
            if not url or not token:
                logger.error("Для source='max' обязательны url и token")
                return {"status": "error", "message": "missing url/token"}

            # Официальный заголовок для MAX (Bearer + token из payload)
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "image/*"
            }

            logger.info(f"Скачивание картинки через Authorization Bearer (MAX 2026): {url}")

            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()

            # Сохраняем во временный файл
            media_root = os.getenv("DJANGO_MEDIA_ROOT", "media")
            os.makedirs(media_root, exist_ok=True)

            # Убираем query-параметры из имени файла
            clean_filename = os.path.basename(url.split('?')[0])
            filename = f"max_{chat_id or 'unknown'}_{clean_filename}"
            temp_file_path = os.path.join(media_root, filename)

            with open(temp_file_path, "wb") as f:
                f.write(resp.content)

            local_path = temp_file_path
            original_photo_path = url
            group_name = group_name or f"chat_{chat_id}"

        elif source == "local":
            if not local_path or not os.path.exists(local_path):
                logger.error(f"Файл не найден (source=local): {local_path}")
                return {"status": "error", "message": "file not found"}
        else:
            logger.warning(f"Неизвестный source={source}")

        # --- ШАГ 2: Распознавание номера ---
        plate, crop_path = recognize_plate(local_path)

        if not plate:
            logger.info(f"Пропуск (невалидный номер): {local_path}")
            return _cleanup_and_return(local_path, temp_file_path, {"status": "skipped", "plate": None})

        # --- ШАГ 3: Создание записи в БД ---
        record = CarPhotoRecord(
            group_name=group_name or "default-group",
            photo_path=original_photo_path,
            status="success",
            plate_number=plate,
        )

        try:
            with open(local_path, "rb") as f:
                record.original_image.save(os.path.basename(local_path), File(f), save=False)
        except Exception as e:
            logger.warning(f"Не удалось сохранить оригинал: {e}")

        if crop_path and os.path.exists(crop_path):
            try:
                with open(crop_path, "rb") as f:
                    record.crop_image.save(os.path.basename(crop_path), File(f), save=False)
            except Exception as e:
                logger.warning(f"Не удалось сохранить кроп: {e}")

        record.save()
        logger.info(f"Запись создана id={record.id} | {plate} | группа={group_name}")

        # --- ШАГ 4: Очистка временных файлов ---
        return _cleanup_and_return(local_path, temp_file_path, {"status": "success", "id": record.id, "plate": plate})

    except Exception as e:
        logger.exception(f"Ошибка process_photo_task: {e}")
        raise self.retry(exc=e)


def _cleanup_and_return(local_path, temp_file_path, result):
    """Удаляет временные файлы и возвращает результат"""
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            os.remove(temp_file_path)
            logger.debug(f"Временный файл удалён: {temp_file_path}")
        except Exception:
            pass

    if local_path and local_path != temp_file_path and os.path.exists(local_path):
        try:
            os.remove(local_path)
            logger.debug(f"Исходный файл удалён: {local_path}")
        except Exception:
            pass

    return result