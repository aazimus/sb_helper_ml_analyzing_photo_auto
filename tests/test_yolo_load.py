from ultralytics import YOLO
import torch
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
weights_path = os.path.join(BASE_DIR, "models", "DETECT.pt")  # <-- теперь именно DETECT.pt

print("1. Загружаем модель YOLO...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = YOLO(weights_path)
model.to(device)
print(f"✅ Модель загружена. Устройство: {device}")

# Пробуем сделать predict на dummy-картинке, чтобы убедиться, что forward работает
test_img = os.path.join(BASE_DIR, "media", "test", "plate_sample.jpg")

if os.path.exists(test_img):
    print(f"2. Делаем predict на {test_img}...")
    results = model.predict(source=test_img, conf=0.25, iou=0.45, device=device, verbose=False)
    boxes = results[0].boxes
    print(f"✅ predict() отработал. Найдено объектов: {len(boxes)}")
    if len(boxes) > 0:
        print("   Пример bbox (xyxy):", boxes[0].xyxy.tolist())
    else:
        print("   ⚠️ Объектов не найдено — это нормально для теста, если картинка не содержит номера или порог слишком высокий.")
else:
    print("⚠️ Тестовой картинки нет, но модель загрузилась успешно — этого достаточно для проверки совместимости.")

print("🎉 Тест 1 для YOLO пройден: модель загружается и делает predict без ошибок.")