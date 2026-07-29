import cv2
import easyocr
import logging

# Инициализируем логгер, чтобы видеть отладочные сообщения в консоли Django
logger = logging.getLogger(__name__)

# Создаём reader один раз при старте (не в каждом запросе!)
# Важно: обязательно 'ru', иначе кириллицу не увидит
reader = easyocr.Reader(['ru', 'en'], verbose=False)

def recognize_plate(image_path: str) -> str | None:
    """
    Возвращает распознанный номер (строка) или None, если не найден.
    """
    try:
        # 1. Читаем картинку через OpenCV (это будет BGR)
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Не удалось прочитать файл: {image_path}")
            return None

        logger.info(f"Изображение загружено: размер={img.shape}, тип={img.dtype}")

        # 2. Конвертируем BGR -> RGB, потому что EasyOCR ожидает RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # 3. Запускаем OCR
        result = reader.readtext(img_rgb)
        logger.info(f"Результат OCR (сырой): {result}")

        # Если ничего не нашли — возвращаем None
        if not result:
            return None

        # Берем самый первый найденный текст (обычно это и есть номер)
        plate_text = result[0][1]
        logger.info(f"Распознан номер: {plate_text}")
        return plate_text

    except Exception as e:
        logger.exception(f"Ошибка в recognize_plate: {e}")
        return None