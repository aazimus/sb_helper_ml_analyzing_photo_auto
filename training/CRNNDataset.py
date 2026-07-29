import os
from pathlib import Path
import csv
import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import numpy as np

# ---------------------------------------------------------
# 1. КЛАСС DATASET
# ---------------------------------------------------------
class CRNNDataset(Dataset):
    def __init__(self, csv_path: str, charset_path: str, img_height=32, max_width=256):
        self.img_height = img_height
        self.max_width = max_width

        with open(charset_path, "r", encoding="utf-8") as f:
            self.charset = json.load(f)
        self.char_to_idx = self.charset
        self.idx_to_char = {idx: ch for ch, idx in self.charset.items()}
        self.num_classes = len(self.charset)

        self.samples = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                img_path = row["path"]
                label = row["label"]
                if any(ch not in self.char_to_idx for ch in label):
                    continue
                self.samples.append((img_path, label))

    def _preprocess_image(self, img_path: str) -> torch.Tensor:
        image = Image.open(img_path).convert("L")
        w, h = image.size
        new_h = self.img_height
        new_w = int(w * (new_h / h))
        if new_w > self.max_width:
            new_w = self.max_width
            new_h = int(h * (new_w / w))

        image = image.resize((new_w, new_h), Image.BILINEAR)
        pad_w = self.max_width - new_w
        padded = Image.new("L", (self.max_width, self.img_height), color=255)
        padded.paste(image, (0, 0))

        tensor = torch.from_numpy(np.array(padded, dtype=np.float32) / 255.0)
        tensor = tensor.unsqueeze(0)  # [1, H, W]
        return tensor

    def _encode_label(self, label: str):
        indices = [self.char_to_idx[ch] for ch in label]
        return torch.tensor(indices, dtype=torch.long)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image_tensor = self._preprocess_image(img_path)
        label_tensor = self._encode_label(label)
        # Возвращаем label_str только для отладки, в обучении не используется
        return image_tensor, label_tensor, label


# ---------------------------------------------------------
# 2. collate_fn для CTC (самое важное исправление!)
# ---------------------------------------------------------
def ctc_collate_fn(batch):
    """
    batch — это список кортежей: [(img_tensor, label_tensor, label_str), ...]
    Мы должны:
      - собрать картинки в один тензор (тут всё ок, они одинакового размера)
      - лейблы НЕ стэкать, а оставить списком + посчитать их длины
    """
    images = [item[0] for item in batch]
    labels = [item[1] for item in batch]
    label_strings = [item[2] for item in batch]

    # Картинки можно стэковать, они все одинакового размера
    images_tensor = torch.stack(images, dim=0)  # [B, 1, H, W]

    # Лейблы остаются списком тензоров разной длины
    # target_lengths — длины каждого лейбла в батче
    target_lengths = torch.tensor([len(l) for l in labels], dtype=torch.int32)
    targets = torch.cat(labels)  # один длинный тензор всех индексов подряд

    return images_tensor, targets, target_lengths, label_strings


# ---------------------------------------------------------
# 3. ЗАГЛУШКА МОДЕЛИ
# ---------------------------------------------------------
class DummyCRNN(nn.Module):
    def __init__(self, num_classes: int, max_seq_len: int = 64):
        super().__init__()
        self.num_classes = num_classes
        self.max_seq_len = max_seq_len

    def forward(self, x: torch.Tensor):
        B, C, H, W = x.shape
        T = self.max_seq_len
        out = torch.randn(T, B, self.num_classes)
        log_probs = torch.log_softmax(out, dim=-1)
        return log_probs


# ---------------------------------------------------------
# 4. ПРОВЕРКА (MAIN)
# ---------------------------------------------------------
if __name__ == "__main__":
    csv_path = Path("data/train/labels_final.csv")
    charset_path = Path("data/charset.json")

    if not csv_path.exists():
        print(f"❌ Файл CSV не найден: {csv_path}")
        exit(1)
    if not charset_path.exists():
        print(f"❌ Файл charset не найден: {charset_path}")
        exit(1)

    print("📂 Загружаем датасет...")
    dataset = CRNNDataset(str(csv_path), str(charset_path))
    print(f"✅ Датасет загружен: {len(dataset)} примеров")

    print("\n🖼 Первые 5 номеров:")
    for i in range(min(5, len(dataset))):
        _, _, label_str = dataset[i]
        print(f"{i+1}. {label_str}")

    # ВАЖНО: передаём collate_fn, чтобы не было stack по разным длинам
    loader = DataLoader(
        dataset,
        batch_size=4,
        shuffle=False,
        num_workers=0,
        collate_fn=ctc_collate_fn
    )
    print(f"📦 DataLoader создан с collate_fn")

    model = DummyCRNN(num_classes=dataset.num_classes, max_seq_len=64)
    criterion = nn.CTCLoss(blank=0, zero_infinity=True)

    print("\n⚡ Считаем loss на одном батче (проверка пайплайна)...")
    try:
        images, targets, target_lengths, _ = next(iter(loader))
        B = images.shape[0]

        log_probs = model(images)  # [T, B, num_classes]

        # Длины входов — одинаковые для всех в батче (по T)
        input_lengths = torch.full((B,), log_probs.size(0), dtype=torch.int32)

        loss = criterion(log_probs, targets, input_lengths, target_lengths)
        print(f"✅ Loss успешно посчитан: {loss.item():.4f}")
        print("🎉 Пайплайн Dataset → DataLoader → CTC Loss работает!")
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")