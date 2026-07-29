import os
import json
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import pandas as pd
from tqdm import tqdm

# ---------------------------------------------------------
# CRNN (точно такая же, как при обучении)
# ---------------------------------------------------------
class CRNN(nn.Module):
    def __init__(self, num_classes: int):
        super().__init__()
        
        self.cnn = nn.Sequential(
            nn.Conv2d(1, 64, 3, padding=1), nn.ReLU(True), nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(True), nn.MaxPool2d(2, 2),
            nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(True),
            nn.Conv2d(256, 256, 3, padding=1), nn.ReLU(True), nn.MaxPool2d((2, 1), (2, 1)),
            nn.Conv2d(256, 512, 3, padding=1), nn.BatchNorm2d(512), nn.ReLU(True),
            nn.Conv2d(512, 512, 3, padding=1), nn.ReLU(True), nn.MaxPool2d((2, 1), (2, 1)),
        )
        
        self.rnn = nn.LSTM(
            input_size=512 * 4,
            hidden_size=256,
            num_layers=2,
            bidirectional=True,
            batch_first=True,
            dropout=0.3
        )
        self.classifier = nn.Linear(512, num_classes)

    def forward(self, x):
        x = self.cnn(x)
        b, c, h, w = x.size()
        if h != 4:
            x = nn.functional.adaptive_avg_pool2d(x, (4, w))
            h = 4
        x = x.reshape(b, c * h, w).permute(0, 2, 1)
        x, _ = self.rnn(x)
        x = self.classifier(x)
        x = x.permute(1, 0, 2)
        return nn.functional.log_softmax(x, dim=2)


# ---------------------------------------------------------
# Датасет
# ---------------------------------------------------------
class CRNNDataset(Dataset):
    def __init__(self, csv_path, charset, img_height=64, img_width=384):
        self.img_height = img_height
        self.img_width = img_width
        
        self.char2idx = {ch: i + 1 for i, ch in enumerate(charset)}
        self.idx2char = {i + 1: ch for i, ch in enumerate(charset)}
        
        df = pd.read_csv(csv_path)
        self.samples = list(zip(df["path"], df["label"]))
        
        self.transform = transforms.Compose([
            transforms.Resize((img_height, img_width), interpolation=Image.BILINEAR),
            transforms.Grayscale(num_output_channels=1),
            transforms.ToTensor(),
        ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        img = self.transform(img)
        return img, label


def collate_fn(batch):
    images, raw = zip(*batch)
    images = torch.stack(images)
    return images, raw


# ---------------------------------------------------------
# Декодер (тот же, что использовался при обучении)
# ---------------------------------------------------------
def decode_smart(log_probs, idx2char, blank=0):
    probs = log_probs.exp()
    _, idxs = probs.max(dim=-1)
    idxs = idxs.cpu().numpy()
    B = idxs.shape[1]
    results = []
    
    for b in range(B):
        seq = []
        prev = blank
        i = 0
        T = idxs.shape[0]
        
        while i < T:
            idx = idxs[i, b]
            
            if idx == blank:
                prev = blank
                i += 1
                continue
            
            j = i
            while j < T and idxs[j, b] == idx:
                j += 1
            run_length = j - i
            conf = float(probs[i, b, idx])
            ch = idx2char.get(idx, "")
            
            emit = 1
            
            if run_length >= 5 and conf > 0.55:
                emit = 2
            elif run_length >= 4 and conf > 0.70:
                emit = 2
            
            if ch == "0" and conf > 0.30 and run_length >= 2:
                emit = max(emit, 1)
            
            if emit == 1 and idx == prev:
                emit = 0
            
            for _ in range(emit):
                seq.append(idx)
                prev = idx
            
            i = j
        
        results.append("".join(idx2char.get(i, "") for i in seq))
    return results


# ---------------------------------------------------------
# Создание test.csv из data/test/ann
# ---------------------------------------------------------
def create_test_csv(test_root="data/test", output_csv="data/test.csv"):
    ann_dir = Path(test_root) / "ann"
    img_dir = Path(test_root) / "img"
    
    if not ann_dir.exists():
        raise FileNotFoundError(f"Не найдена папка: {ann_dir}")
    
    rows = []
    missing = 0
    
    for json_path in sorted(ann_dir.glob("*.json")):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        label = data.get("description", "").strip().upper()
        name = data.get("name", json_path.stem)
        
        # Ищем файл изображения (пробуем разные расширения)
        img_path = None
        for ext in [".jpg", ".jpeg", ".png", ".bmp"]:
            candidate = img_dir / f"{name}{ext}"
            if candidate.exists():
                img_path = candidate
                break
        
        if img_path is None:
            # Иногда имя файла совпадает с именем json
            for ext in [".jpg", ".jpeg", ".png", ".bmp"]:
                candidate = img_dir / f"{json_path.stem}{ext}"
                if candidate.exists():
                    img_path = candidate
                    break
        
        if img_path is None:
            missing += 1
            continue
        
        rows.append({
            "path": str(img_path).replace("\\", "/"),
            "label": label
        })
    
    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False)
    
    print(f"Создан {output_csv}")
    print(f"  Всего примеров: {len(df)}")
    print(f"  Пропущено (нет картинки): {missing}")
    return output_csv


# ---------------------------------------------------------
# Основной код
# ---------------------------------------------------------
if __name__ == "__main__":
    CHECKPOINT = "checkpoints/crnn_best.pth"
    TEST_CSV = "data/test.csv"
    CHARSET = "0123456789ABCEHKMOPTXY"
    BATCH_SIZE = 32
    IMG_H = 64
    IMG_W = 384
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    
    # 1. Создаём test.csv
    print("\n=== Создание test.csv ===")
    create_test_csv(test_root="data/test", output_csv=TEST_CSV)
    
    # 2. Загружаем чекпоинт
    print("\n=== Загрузка модели ===")
    if not os.path.isfile(CHECKPOINT):
        raise FileNotFoundError(f"Чекпоинт не найден: {CHECKPOINT}")
    
    checkpoint = torch.load(CHECKPOINT, map_location=device, weights_only=False)
    
    charset = checkpoint.get("charset", CHARSET)
    img_h = checkpoint.get("img_height", IMG_H)
    img_w = checkpoint.get("img_width", IMG_W)
    best_val_acc = checkpoint.get("val_acc", 0.0)
    epoch = checkpoint.get("epoch", "?")
    
    print(f"Чекпоинт: {CHECKPOINT}")
    print(f"  Эпоха: {epoch}")
    print(f"  Val Acc при сохранении: {best_val_acc:.4f}")
    print(f"  Charset: {charset}")
    
    num_classes = len(charset) + 1
    model = CRNN(num_classes).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    
    # 3. Датасет и лоадер
    test_ds = CRNNDataset(TEST_CSV, charset, img_h, img_w)
    test_loader = DataLoader(
        test_ds,
        batch_size=BATCH_SIZE,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=4,
        pin_memory=True
    )
    
    print(f"Тестовых примеров: {len(test_ds)}")
    
    # 4. Инференс
    print("\n=== Тестирование ===")
    correct = 0
    total = 0
    errors = []
    
    with torch.no_grad():
        for imgs, raw_labels in tqdm(test_loader, desc="Test"):
            imgs = imgs.to(device)
            preds = decode_smart(model(imgs), test_ds.idx2char)
            
            for pred, true in zip(preds, raw_labels):
                total += 1
                if pred == true:
                    correct += 1
                else:
                    errors.append((pred, true))
    
    acc = correct / max(total, 1)
    
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТ НА TEST")
    print("=" * 60)
    print(f"Точность: {acc:.4f}  ({correct}/{total})")
    print(f"Ошибок:   {len(errors)}")
    print("=" * 60)
    
    # 5. Показываем ошибки
    if errors:
        print("\nПримеры ошибок (первые 30):")
        print("-" * 55)
        for i, (pred, true) in enumerate(errors[:30]):
            print(f"  ❌ Pred: {pred:14} | True: {true}")
        if len(errors) > 30:
            print(f"  ... и ещё {len(errors) - 30} ошибок")
    else:
        print("\nОшибок нет!")
    
    # 6. Несколько правильных примеров
    print("\nПримеры правильных предсказаний:")
    print("-" * 55)
    shown = 0
    with torch.no_grad():
        for imgs, raw_labels in test_loader:
            preds = decode_smart(model(imgs.to(device)), test_ds.idx2char)
            for pred, true in zip(preds, raw_labels):
                if pred == true:
                    print(f"  ✅ Pred: {pred:14} | True: {true}")
                    shown += 1
                    if shown >= 10:
                        break
            if shown >= 10:
                break