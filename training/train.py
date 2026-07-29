from ultralytics import YOLO

model = YOLO("yolov8n.pt")

results = model.train(
    data="data.yaml",
    epochs=10,
    imgsz=640,
    batch=8,
    name="plate_detector",
    patience=3,
)