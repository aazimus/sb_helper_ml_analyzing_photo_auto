# tests/emul_max_webhhok_service.py
"""
Эмулятор webhook-сервиса.
Следит за папкой, при появлении нового фото отправляет webhook в Django.
"""

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
TARGET_URL = "http://localhost:8000/api/webhook/"          # важно: /api/
WATCH_FOLDER = Path("tests/emul_max_group")                # папка с тестовыми фото
PROCESSED_MARKER_EXT = ".sent"

# Можно поменять группу
DEFAULT_GROUP = "test-group"

# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("emulator")


class PhotoHandler(FileSystemEventHandler):
    def on_created(self, event):
        path = Path(event.src_path)

        # Пропускаем папки и уже обработанные файлы
        if path.is_dir():
            return
        if path.name.endswith(PROCESSED_MARKER_EXT):
            return
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            logger.debug(f"Пропущен файл: {path.name}")
            return

        logger.info(f"Обнаружен новый файл: {path.name}")

        # Ждём, пока файл полностью запишется на диск
        time.sleep(0.7)

        try:
            self.send_webhook(path)

            # Ставим маркер, чтобы не отправить повторно
            marker = path.with_suffix(path.suffix + PROCESSED_MARKER_EXT)
            marker.touch()
            logger.info(f"[OK] Отправлен webhook + создан маркер: {marker.name}")

        except Exception as e:
            logger.error(f"[ERROR] Не удалось обработать {path.name}: {e}", exc_info=True)

    def send_webhook(self, photo_path: Path):
        payload = {
            "event": "new_photo",
            "chat_id": DEFAULT_GROUP,
            "user_id": "emulator-user",
            "file": {
                "name": photo_path.name,
                "path": str(photo_path.resolve()),          # абсолютный путь
                "size": photo_path.stat().st_size,
                "mime_type": "image/jpeg" if photo_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
            },
            "timestamp": time.time()
        }

        logger.info(f"→ Отправка на {TARGET_URL}")
        logger.debug(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")

        resp = requests.post(
            TARGET_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        resp.raise_for_status()

        try:
            data = resp.json()
            logger.info(
                f"Ответ сервера: id={data.get('id')} | "
                f"status={data.get('status')} | "
                f"plate={data.get('plate_number')}"
            )
        except Exception:
            logger.info(f"Ответ сервера: {resp.status_code} — {resp.text}")


if __name__ == "__main__":
    WATCH_FOLDER.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("Эмулятор webhook запущен")
    logger.info(f"Мониторинг папки : {WATCH_FOLDER.resolve()}")
    logger.info(f"Webhook URL      : {TARGET_URL}")
    logger.info("Кидай фото в папку — они уйдут на распознавание")
    logger.info("=" * 60)

    event_handler = PhotoHandler()
    observer = Observer()
    observer.schedule(event_handler, str(WATCH_FOLDER), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Остановка эмулятора...")
        observer.stop()

    observer.join()
    logger.info("Эмулятор остановлен")