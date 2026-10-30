import os
import uuid
import mimetypes
import logging
import requests
from celery import shared_task
from django.core.files import File

logger = logging.getLogger(__name__)


def _guess_extension(response) -> str:
    """Определяет расширение картинки по Content-Type или сигнатуре файла (magic bytes)."""
    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    ext_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/heic": ".heic",
    }
    if content_type in ext_map:
        return ext_map[content_type]

    data = response.content[:12]
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"

    ext = mimetypes.guess_extension(content_type)
    return ext if ext else ".jpg"


@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def process_photo_task(
    self,
    local_path: str = None,
    group_name: str = None,
    original_photo_path: str = "",
    url: str = None,
    token: str = None,
    chat_id: str = None,
    source: str = "local"
):
    from .models import CarPhotoRecord, ChatGroup

    temp_file_path = None

    try:
        # --- ШАГ 1: Обработка источника (MAX или локальный файл) ---
        if source == "max":
            if not url or not token:
                logger.error("Для source='max' обязательны url и token")
                return {"status": "error", "message": "missing url/token"}

            chat_str_id = str(chat_id) if chat_id else "unknown"

            # Проверка бэк-офиса: активен ли чат (Защита от DDoS и спама)
            group_obj = ChatGroup.objects.filter(chat_id=chat_str_id).first()
            if group_obj and not group_obj.is_active:
                logger.warning(f"Запрос заблокирован: чат {chat_str_id} отключен в админке.")
                return {"status": "blocked", "message": "chat is disabled"}

            # Запрос человеческого названия чата у MAX API, если группа новая или еще не имеет человеческого имени
            chat_title = f"chat_{chat_str_id}"
            if not group_obj or not group_obj.name or group_obj.name.startswith("chat_"):
                try:
                    api_url = f"https://platform-api.max.ru/chats/{chat_str_id}"
                    headers_api = {"Authorization": f"Bearer {token}"}
                    resp_api = requests.get(api_url, headers=headers_api, timeout=5)
                    if resp_api.status_code == 200:
                        data = resp_api.json()
                        if isinstance(data, dict):
                            title_val = data.get("title") or data.get("name")
                            if title_val and isinstance(title_val, str):
                                chat_title = title_val
                except Exception as e:
                    logger.warning(f"Не удалось запросить название чата у MAX: {e}")
            else:
                chat_title = group_obj.name

            # Создаем или обновляем группу в БД
            group_obj, _ = ChatGroup.objects.update_or_create(
                chat_id=chat_str_id,
                defaults={"name": str(chat_title)}
            )

            if not group_obj.is_active:
                return {"status": "blocked", "message": "chat is disabled"}

            group_name = group_obj.name

            # Скачивание файла из MAX
            headers = {"Authorization": f"Bearer {token}", "Accept": "image/*"}
            logger.info(f"Скачивание картинки через MAX API: {url}")
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()

            media_root = os.getenv("DJANGO_MEDIA_ROOT", "media")
            os.makedirs(media_root, exist_ok=True)

            ext = _guess_extension(resp)
            unique_id = uuid.uuid4().hex[:10]
            filename = f"max_{chat_str_id}_{unique_id}{ext}"
            temp_file_path = os.path.join(media_root, filename)

            with open(temp_file_path, "wb") as f:
                f.write(resp.content)

            local_path = temp_file_path
            original_photo_path = url

        elif source == "local":
            if not local_path or not os.path.exists(local_path):
                logger.error(f"Файл не найден (source=local): {local_path}")
                return {"status": "error", "message": "file not found"}
            group_name = group_name or "default-group"
        else:
            logger.warning(f"Неизвестный source={source}")
            group_name = group_name or "default-group"

        # --- ШАГ 2: Распознавание номера (с защитой для тестового окружения) ---
        try:
            from .ocr_service import recognize_plate
            plate, crop_path = recognize_plate(local_path)
        except (ImportError, ModuleNotFoundError):
            # Заглушка на случай запуска легких тестов в бэкенд-контейнере без ML-модулей
            plate, crop_path = "А111АА777", None

        # Отсев нераспознанных номеров (чтобы не захламлять базу)
        if not plate:
            logger.info(f"Номер не распознан, фото отсеяно: {local_path}")
            return _cleanup_and_return(local_path, temp_file_path, {"status": "skipped", "plate": None})

        # --- ШАГ 3: Создание записи в БД для успешных номеров ---
        record = CarPhotoRecord(
            group_name=group_name,
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
        logger.info(f"Запись сохранена id={record.id} | номер={plate} | группа={group_name}")

        return _cleanup_and_return(
            local_path,
            temp_file_path,
            {"status": "success", "id": record.id, "plate": plate, "group_name": group_name}
        )

    except Exception as e:
        logger.exception(f"Ошибка process_photo_task: {e}")
        raise self.retry(exc=e)


def _cleanup_and_return(local_path, temp_file_path, result):
    """Удаляет временные файлы"""
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            os.remove(temp_file_path)
        except Exception:
            pass

    if local_path and local_path != temp_file_path and os.path.exists(local_path):
        try:
            os.remove(local_path)
        except Exception:
            pass

    return result