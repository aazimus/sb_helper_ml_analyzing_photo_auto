from ultralytics import YOLO
from pathlib import Path
import cv2

# ====================== НАСТРОЙКИ ======================
MODEL_PATH = "data/detect_num/best.pt"                    # путь к вашей модели
DATA_YAML = "data.yaml"                   # yaml с путями (или укажите напрямую)
TEST_IMAGES = "data/detect_num/test/images"  # папка с тестовыми картинками
CONF = 0.25                               # порог уверенности
IOU = 0.45                                # порог NMS
SAVE_DIR = "runs/detect/test_results"     # куда сохранять результаты
# =======================================================

def main():
    # 1. Загружаем модель
    model = YOLO(MODEL_PATH)
    print(f"Модель загружена: {MODEL_PATH}")
    print(f"Классы: {model.names}")

    # 2. Валидация на test (если есть data.yaml и labels)
    # Это даст метрики: Precision, Recall, mAP50, mAP50-95
    if Path(DATA_YAML).exists():
        print("\n=== Валидация на test ===")
        metrics = model.val(
            data=DATA_YAML,
            split="test",          # используем именно test
            conf=CONF,
            iou=IOU,
            plots=True,            # сохранит графики
            save_json=True,        # сохранит predictions.json
        )
        print(f"mAP50:     {metrics.box.map50:.4f}")
        print(f"mAP50-95:  {metrics.box.map:.4f}")
        print(f"Precision: {metrics.box.mp:.4f}")
        print(f"Recall:    {metrics.box.mr:.4f}")

    # 3. Предсказание на всех картинках test и сохранение результатов
    print("\n=== Предсказание на test/img ===")
    results = model.predict(
        source=TEST_IMAGES,
        conf=CONF,
        iou=IOU,
        save=True,                 # сохраняет картинки с боксами
        save_txt=True,             # сохраняет .txt с предсказаниями
        save_conf=True,            # добавляет confidence в txt
        project=SAVE_DIR,
        name="predict",
        exist_ok=True,
    )

    # 4. Краткая статистика
    total_dets = 0
    for r in results:
        total_dets += len(r.boxes)
    print(f"\nОбработано изображений: {len(results)}")
    print(f"Всего обнаружено объектов: {total_dets}")
    print(f"Результаты сохранены в: {SAVE_DIR}/predict/")

if __name__ == "__main__":
    main()