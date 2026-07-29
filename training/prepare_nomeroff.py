from pathlib import Path
import json
import csv

# --- НАСТРОЙКИ ПУТЕЙ ---
base_dir = Path("data/train")
img_dir = base_dir / "img"
ann_dir = base_dir / "ann"
output_csv = base_dir / "labels_final.csv"

def extract_label_from_json(data: dict) -> str | None:
    if "description" in data and isinstance(data["description"], str):
        label = data["description"].strip()
        if label:
            return label.upper()
    if "plate" in data and isinstance(data["plate"], str):
        label = data["plate"].strip()
        if label:
            return label.upper()
    if "plates" in data and isinstance(data["plates"], list) and len(data["plates"]) > 0:
        first = data["plates"][0]
        if isinstance(first, str) and first.strip():
            return first.strip().upper()
    return None

def find_image_path(json_path: Path, img_dir: Path) -> Path | None:
    stem = json_path.stem  # имя без расширения
    # Пробуем .png
    candidate = img_dir / (stem + ".png")
    if candidate.exists():
        return candidate
    # Пробуем .jpg
    candidate = img_dir / (stem + ".jpg")
    if candidate.exists():
        return candidate
    return None

def main():
    json_files = list(ann_dir.rglob("*.json"))
    print(f"📂 Найдено JSON-файлов: {len(json_files)}\n")

    rows = []
    skipped_no_img = 0
    skipped_bad_label = 0

    # Покажем первые 20 пар, чтобы ты убедился, что имена совпадают
    show_count = min(20, len(json_files))
    print(f"--- Первые {show_count} пар (для проверки имён) ---")
    for i, json_path in enumerate(json_files):
        stem = json_path.stem
        img_candidate_png = img_dir / (stem + ".png")
        img_candidate_jpg = img_dir / (stem + ".jpg")

        print(f"{i+1}. JSON: {json_path.name}")
        print(f"   → ищем: {img_candidate_png}")
        if not img_candidate_png.exists():
            print(f"   (не найдено) → пробуем: {img_candidate_jpg}")

        # Дальше обычная логика
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            skipped_bad_label += 1
            continue

        label = extract_label_from_json(data)
        if not label:
            skipped_bad_label += 1
            continue
        if not (8 <= len(label) <= 9):
            skipped_bad_label += 1
            continue

        img_path = find_image_path(json_path, img_dir)
        if img_path is None:
            skipped_no_img += 1
            continue

        rows.append([img_path.as_posix(), label])

        if i < show_count:
            print(f"   ✅ OK: {img_path.name} → {label}")
        elif i == show_count:
            print("... (остальные пары обрабатываются без вывода)")

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "label"])
        writer.writerows(rows)

    print(f"\n✅ Готово: {len(rows)} валидных пар в {output_csv}")
    print(f"   - пропущено (нет картинки): {skipped_no_img}")
    print(f"   - пропущено (плохой лейбл): {skipped_bad_label}")

if __name__ == "__main__":
    main()