import os
import json
import torch
import numpy as np
from PIL import Image
from ultralytics import YOLO


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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

yolo_path = os.path.join(BASE_DIR, "models", "DETECT.pt")
crnn_path = os.path.join(BASE_DIR, "models", "CRNN.pth")
charset_path = r"C:\project\car_number_cheking\cheking_number_car\data\charset.json"
test_folder = os.path.join(BASE_DIR, "media", "test")
temp_dir = os.path.join(BASE_DIR, "media", "temp_crops")

device = "cuda" if torch.cuda.is_available() else "cpu"

print("=" * 60)
print("🚀 YOLO + CRNN (латинский charset → кириллица)")
print(f"Device: {device}")
print("=" * 60)

# ---------- charset ----------
print(f"\n📦 Charset: {charset_path}")
with open(charset_path, encoding="utf-8") as f:
    cs = json.load(f)

idx2char = {int(k): v for k, v in cs["idx2char"].items()}
BLANK = cs["blank"]
num_classes = cs["num_classes"]
latin_to_cyr = cs["latin_to_cyrillic"]

print(f"   num_classes = {num_classes}")
print(f"   blank       = {BLANK}")
print(f"   charset     = {cs['charset']}")

# ---------- YOLO ----------
print(f"\n📦 YOLO: {yolo_path}")
yolo = YOLO(yolo_path)
print("✅ YOLO OK")

# ---------- CRNN ----------
print(f"📦 CRNN: {crnn_path}")
crnn = CRNN(num_classes).to(device)
ckpt = torch.load(crnn_path, map_location=device, weights_only=False)

if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
    state = ckpt["model_state_dict"]
    print(f"   epoch={ckpt.get('epoch')}  val_acc={ckpt.get('val_acc')}")
else:
    state = ckpt

crnn.load_state_dict(state, strict=True)
crnn.eval()
print("✅ CRNN OK")

# ---------- картинки ----------
exts = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
images = [
    os.path.join(test_folder, f)
    for f in sorted(os.listdir(test_folder))
    if f.lower().endswith(exts)
]
print(f"\n📸 Картинок: {len(images)}")
os.makedirs(temp_dir, exist_ok=True)

for img_path in images:
    name = os.path.basename(img_path)
    print(f"\n--- {name} ---")

    results = yolo.predict(source=img_path, conf=0.25, iou=0.45, device=device, verbose=False)
    boxes = results[0].boxes
    print(f"   YOLO boxes: {len(boxes)}")

    img_full = Image.open(img_path).convert("RGB")
    crops = []

    if len(boxes) == 0:
        crops = [img_path]
    else:
        boxes_data = sorted(
            [(box.xyxy[0].cpu().numpy().astype(int), float(box.conf[0])) for box in boxes],
            key=lambda x: x[0][0]
        )
        for i, (xyxy, conf) in enumerate(boxes_data):
            x1, y1, x2, y2 = xyxy
            pad_w = max(2, int((x2 - x1) * 0.08))
            pad_h = max(2, int((y2 - y1) * 0.15))
            x1, y1 = max(0, x1 - pad_w), max(0, y1 - pad_h)
            x2, y2 = min(img_full.width, x2 + pad_w), min(img_full.height, y2 + pad_h)

            crop = img_full.crop((x1, y1, x2, y2))
            crop_path = os.path.join(temp_dir, f"{os.path.splitext(name)[0]}_crop_{i}.jpg")
            crop.save(crop_path, quality=95)
            crops.append(crop_path)
        print(f"   кропов: {len(crops)}")

    for i, crop_path in enumerate(crops):
        try:
            tensor = preprocess_image(crop_path).to(device)
            with torch.no_grad():
                log_probs = crnn(tensor)

            if images.index(img_path) < 3 and i == 0:
                raw_idxs = log_probs.argmax(dim=-1).cpu().numpy().flatten()[:40]
                print(f"   [debug] raw idxs = {raw_idxs.tolist()}")

            number_lat = decode_single(log_probs, idx2char, blank=BLANK)
            number_cyr = to_cyrillic(number_lat, latin_to_cyr)

            print(f"   Crop {i}: → «{number_cyr}»  (lat: {number_lat})")
        except Exception as e:
            print(f"   ❌ {e}")

print("\n🎉 Готово")