import os
import json
import logging
import torch
import numpy as np
from PIL import Image
from ultralytics import YOLO
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Пути
# ---------------------------------------------------------
BASE_DIR = settings.BASE_DIR

YOLO_PATH = os.path.join(BASE_DIR, "models", "DETECT.pt")
CRNN_PATH = os.path.join(BASE_DIR, "models", "CRNN.pth")
CHARSET_PATH = os.path.join(BASE_DIR, "data", "charset.json")
TEMP_CROPS_DIR = os.path.join(BASE_DIR, "media", "temp_crops")

os.makedirs(TEMP_CROPS_DIR, exist_ok=True)

device = "cuda" if torch.cuda.is_available() else "cpu"


# ---------------------------------------------------------
# CRNN
# ---------------------------------------------------------
class CRNN(torch.nn.Module):
    def __init__(self, num_classes: int):
        super().__init__()
        self.cnn = torch.nn.Sequential(
            torch.nn.Conv2d(1, 64, 3, padding=1), torch.nn.ReLU(True), torch.nn.MaxPool2d(2, 2),
            torch.nn.Conv2d(64, 128, 3, padding=1), torch.nn.ReLU(True), torch.nn.MaxPool2d(2, 2),
            torch.nn.Conv2d(128, 256, 3, padding=1), torch.nn.BatchNorm2d(256), torch.nn.ReLU(True),
            torch.nn.Conv2d(256, 256, 3, padding=1), torch.nn.ReLU(True), torch.nn.MaxPool2d((2, 1), (2, 1)),
            torch.nn.Conv2d(256, 512, 3, padding=1), torch.nn.BatchNorm2d(512), torch.nn.ReLU(True),
            torch.nn.Conv2d(512, 512, 3, padding=1), torch.nn.ReLU(True), torch.nn.MaxPool2d((2, 1), (2, 1)),
        )
        self.rnn = torch.nn.LSTM(
            input_size=512 * 4,
            hidden_size=256,
            num_layers=2,
            bidirectional=True,
            batch_first=True,
            dropout=0.3
        )
        self.classifier = torch.nn.Linear(512, num_classes)

    def forward(self, x):
        x = self.cnn(x)
        b, c, h, w = x.size()
        if h != 4:
            x = torch.nn.functional.adaptive_avg_pool2d(x, (4, w))
            h = 4
        x = x.reshape(b, c * h, w).permute(0, 2, 1)
        x, _ = self.rnn(x)
        x = self.classifier(x)
        x = x.permute(1, 0, 2)
        return torch.nn.functional.log_softmax(x, dim=2)


def preprocess_image(image_path: str, img_height=64, img_width=384):
    image = Image.open(image_path).convert("RGB")
    image = image.resize((img_width, img_height), Image.BILINEAR)
    image = image.convert("L")
    tensor = torch.from_numpy(np.array(image, dtype=np.float32) / 255.0)
    return tensor.unsqueeze(0).unsqueeze(0)


def decode_single(log_probs, idx2char, blank=0):
    idxs = log_probs.argmax(dim=-1).cpu().numpy()
    if idxs.ndim == 2:
        idxs = idxs[:, 0]

    seq = []
    prev = blank
    for idx in idxs:
        idx = int(idx)
        if idx == blank or idx == prev:
            prev = idx
            continue
        ch = idx2char.get(idx, "")
        if ch:
            seq.append(ch)
        prev = idx
    return "".join(seq)


def to_cyrillic(text: str, mapping: dict) -> str:
    return "".join(mapping.get(c, c) for c in text)


# ---------------------------------------------------------
# Проверка качества кропа
# ---------------------------------------------------------
def is_bad_crop(image_path: str) -> bool:
    try:
        img = Image.open(image_path).convert("L")
        arr = np.array(img, dtype=np.float32) / 255.0
        mean_val = arr.mean()
        std_val = arr.std()

        if mean_val > 0.85 and std_val < 0.08:
            return True
        if mean_val < 0.08 and std_val < 0.05:
            return True
        if arr.shape[0] < 15 or arr.shape[1] < 40:
            return True
        return False
    except Exception:
        return True


# ---------------------------------------------------------
# Постобработка российских номеров
# ---------------------------------------------------------
ALLOWED_LETTERS = set("АВЕКМНОРСТУХ")

CONFUSION_MAP = {
    'Х': 'Н',
    'Н': 'Х',
    'О': '0',
    '0': 'О',
    'В': '8',
    '8': 'В',
}


def normalize_plate(text: str) -> str:
    return "".join(c for c in text.upper() if c.isalnum())


def is_valid_ru_plate(plate: str) -> bool:
    plate = normalize_plate(plate)
    if len(plate) not in (8, 9):
        return False

    letter1 = plate[0]
    digits = plate[1:4]
    letters2 = plate[4:6]
    region = plate[6:]

    if letter1 not in ALLOWED_LETTERS:
        return False
    if not digits.isdigit():
        return False
    if not all(c in ALLOWED_LETTERS for c in letters2):
        return False
    if not region.isdigit() or len(region) not in (2, 3):
        return False
    return True


def try_fix_plate(raw: str) -> str | None:
    plate = normalize_plate(raw)
    if not plate:
        return None
    if is_valid_ru_plate(plate):
        return plate

    candidates = set()
    for i, char in enumerate(plate):
        if char in CONFUSION_MAP:
            candidates.add(plate[:i] + CONFUSION_MAP[char] + plate[i+1:])

    if len(plate) in (7, 8) and plate[0] in ALLOWED_LETTERS and plate[1:3].isdigit():
        candidates.add(plate[0] + "1" + plate[1:])

    if len(plate) == 10:
        candidates.add(plate[:9])
        candidates.add(plate[1:])

    for cand in candidates:
        if is_valid_ru_plate(cand):
            return cand
    return None


# ---------------------------------------------------------
# Ленивая загрузка моделей
# ---------------------------------------------------------
_yolo = None
_crnn = None
_idx2char = None
_BLANK = 0
_latin_to_cyr = None


def _load_models():
    global _yolo, _crnn, _idx2char, _BLANK, _latin_to_cyr

    if _yolo is not None:
        return

    logger.info("=" * 50)
    logger.info("Загрузка YOLO + CRNN моделей...")
    logger.info(f"Device: {device}")

    if not os.path.exists(YOLO_PATH):
        raise FileNotFoundError(f"Не найден DETECT.pt: {YOLO_PATH}")
    if not os.path.exists(CRNN_PATH):
        raise FileNotFoundError(f"Не найден CRNN.pth: {CRNN_PATH}")
    if not os.path.exists(CHARSET_PATH):
        raise FileNotFoundError(f"Не найден charset.json: {CHARSET_PATH}")

    with open(CHARSET_PATH, encoding="utf-8") as f:
        cs = json.load(f)

    _idx2char = {int(k): v for k, v in cs["idx2char"].items()}
    _BLANK = cs["blank"]
    _latin_to_cyr = cs["latin_to_cyrillic"]
    num_classes = cs["num_classes"]

    _yolo = YOLO(YOLO_PATH)
    logger.info("YOLO загружен")

    _crnn = CRNN(num_classes).to(device)
    ckpt = torch.load(CRNN_PATH, map_location=device, weights_only=False)
    state = ckpt["model_state_dict"] if isinstance(ckpt, dict) and "model_state_dict" in ckpt else ckpt
    _crnn.load_state_dict(state, strict=True)
    _crnn.eval()
    logger.info("CRNN загружен")
    logger.info("=" * 50)


def recognize_plate(image_path: str) -> tuple[str | None, str | None]:
    """
    Возвращает (валидный_номер, путь_к_кропу) или (None, None)
    """
    try:
        _load_models()

        if not os.path.exists(image_path):
            logger.error(f"Файл не найден: {image_path}")
            return None, None

        logger.info(f"Обработка: {image_path}")

        results = _yolo.predict(
            source=image_path,
            conf=0.30,
            iou=0.45,
            device=device,
            verbose=False
        )
        boxes = results[0].boxes
        logger.info(f"YOLO boxes: {len(boxes)}")

        img_full = Image.open(image_path).convert("RGB")
        crops_info = []

        if len(boxes) == 0:
            logger.info("YOLO ничего не нашёл")
            return None, None

        boxes_data = sorted(
            [(box.xyxy[0].cpu().numpy().astype(int), float(box.conf[0])) for box in boxes],
            key=lambda x: x[0][0]
        )

        for i, (xyxy, conf) in enumerate(boxes_data):
            x1, y1, x2, y2 = xyxy
            pad_w = max(2, int((x2 - x1) * 0.10))
            pad_h = max(2, int((y2 - y1) * 0.18))
            x1 = max(0, x1 - pad_w)
            y1 = max(0, y1 - pad_h)
            x2 = min(img_full.width, x2 + pad_w)
            y2 = min(img_full.height, y2 + pad_h)

            crop = img_full.crop((x1, y1, x2, y2))
            crop_name = f"{os.path.splitext(os.path.basename(image_path))[0]}_crop_{i}.jpg"
            crop_path = os.path.join(TEMP_CROPS_DIR, crop_name)
            crop.save(crop_path, quality=95)

            if is_bad_crop(crop_path):
                logger.info(f"Crop {i}: отброшен (плохой кроп)")
                continue

            try:
                tensor = preprocess_image(crop_path).to(device)
                with torch.no_grad():
                    log_probs = _crnn(tensor)

                number_lat = decode_single(log_probs, _idx2char, blank=_BLANK)
                number_cyr = to_cyrillic(number_lat, _latin_to_cyr)
                cleaned = normalize_plate(number_cyr)

                logger.info(f"Crop {i}: «{number_cyr}» → «{cleaned}» (conf={conf:.2f})")
                score = len(cleaned) + conf
                crops_info.append((crop_path, number_cyr, score))
            except Exception as e:
                logger.warning(f"Ошибка на кропе {i}: {e}")

        if not crops_info:
            logger.warning("Нет подходящих кропов")
            return None, None

        best = max(crops_info, key=lambda x: x[2])
        raw_plate = best[1]
        best_crop = best[0]

        fixed = try_fix_plate(raw_plate)

        if fixed and is_valid_ru_plate(fixed):
            logger.info(f"Сырой: «{raw_plate}» → Валидный: «{fixed}»")
            return fixed, best_crop

        logger.info(f"Номер не прошёл валидацию: «{raw_plate}»")
        return None, best_crop

    except Exception as e:
        logger.exception(f"Ошибка в recognize_plate: {e}")
        return None, None