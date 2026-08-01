# chek_n/tasks.py
import os
import logging
from celery import shared_task
from django.core.files import File

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def process_photo_task(self, local_path: str, group_name: str, original_photo_path: str):
    from .ocr_service import recognize_plate
    from .models import CarPhotoRecord

    try:
        if not os.path.exists(local_path):
            logger.error(f"Файл не найден: {local_path}")
            return {'status': 'error', 'message': 'file not found'}

        plate, crop_path = recognize_plate(local_path)

        if not plate:
            logger.info(f"Пропуск (невалидный номер): {local_path}")
            try:
                os.remove(local_path)
            except Exception:
                pass
            return {'status': 'skipped', 'plate': None}

        record = CarPhotoRecord(
            group_name=group_name or 'default-group',
            photo_path=original_photo_path,
            status='success',
            plate_number=plate,
        )

        try:
            with open(local_path, 'rb') as f:
                record.original_image.save(
                    os.path.basename(local_path),
                    File(f),
                    save=False
                )
        except Exception as e:
            logger.warning(f"Не удалось сохранить оригинал: {e}")

        if crop_path and os.path.exists(crop_path):
            try:
                with open(crop_path, 'rb') as f:
                    record.crop_image.save(
                        os.path.basename(crop_path),
                        File(f),
                        save=False
                    )
            except Exception as e:
                logger.warning(f"Не удалось сохранить кроп: {e}")

        record.save()
        logger.info(f"Запись создана id={record.id} | {plate} | группа={group_name}")

        try:
            os.remove(local_path)
        except Exception:
            pass

        return {'status': 'success', 'id': record.id, 'plate': plate}

    except Exception as e:
        logger.exception(f"Ошибка process_photo_task: {e}")
        raise self.retry(exc=e)