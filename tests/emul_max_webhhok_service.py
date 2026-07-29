import os
import json
import time
import requests
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ---------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------
TARGET_URL = "http://localhost:8000/webhook/"
WATCH_FOLDER = "cheking_number_car/tests/emul_max_group"          # <-- укажи свою папку
PROCESSED_MARKER_EXT = ".sent"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class PhotoHandler(FileSystemEventHandler):
    def on_created(self, event):
        path = Path(event.src_path)

        # Пропускаем директории и уже обработанные файлы
        if path.is_dir():
            logger.debug(f"Пропущена директория: {path}")
            return
        if path.name.endswith(PROCESSED_MARKER_EXT):
            logger.debug(f"Пропущен маркерный файл: {path.name}")
            return

        logger.info(f"Обнаружен новый файл: {path.name} ({path})")

        # Небольшая задержка, чтобы файл точно дописался (актуально при сохранении из редактора/IDE)
        time.sleep(0.5)

        try:
            self.send_webhook(path)
            # Ставим маркер, чтобы не отправить повторно
            marker = path.with_suffix(path.suffix + PROCESSED_MARKER_EXT)
            marker.touch()
            logger.info(f"[OK] Отправлен webhook для {path.name}, создан маркер: {marker.name}")
        except Exception as e:
            logger.error(f"[ERROR] Не удалось отправить webhook для {path.name}: {e}", exc_info=True)

    def send_webhook(self, photo_path: Path):
        payload = {
            "event": "new_photo",
            "chat_id": "test-chat-123",
            "user_id": "user-999",
            "file": {
                "name": photo_path.name,
                "path": str(photo_path.absolute()),
                "size": photo_path.stat().st_size,
                "mime_type": "image/jpeg" if photo_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
            },
            "timestamp": time.time()
        }

        logger.debug(f"Отправка payload на {TARGET_URL}: {json.dumps(payload, ensure_ascii=False)}")

        resp = requests.post(
            TARGET_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        resp.raise_for_status()
        logger.info(f"Webhook отправлен, статус: {resp.status_code}, ответ: {resp.text}")


if __name__ == "__main__":
    watch_path = Path(WATCH_FOLDER)
    watch_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Запуск наблюдателя: мониторинг папки {watch_path}")

    event_handler = PhotoHandler()
    observer = Observer()
    observer.schedule(event_handler, str(watch_path), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Остановка наблюдателя по сигналу пользователя")
        observer.stop()
    observer.join()
    logger.info("Наблюдатель остановлен")