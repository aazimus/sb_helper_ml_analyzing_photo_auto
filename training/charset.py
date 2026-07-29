
import csv
from pathlib import Path
import json

csv_path = Path("data/train/labels_final.csv")
charset_path = Path("data/charset.json")

chars = set()

with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        label = row["label"].strip()
        for ch in label:
            chars.add(ch)

# Сортируем для воспроизводимости
sorted_chars = sorted(chars)
charset = {ch: idx for idx, ch in enumerate(sorted_chars)}

with open(charset_path, "w", encoding="utf-8") as f:
    json.dump(charset, f, ensure_ascii=False, indent=2)

print(f"✅ charset создан: {len(charset)} символов в {charset_path}")
print("Примеры символов:", list(charset.keys())[:30])