from ultralytics import YOLO

def main():
    model = YOLO("data/detect_num/best.pt")

    # Полная оценка на test
    metrics = model.val(
        data="data.yaml",
        split="test",
        conf=0.25,
        iou=0.5,
        plots=True,
        save_json=True,
        workers=0,          # ← важно для Windows, отключает multiprocessing
    )

    print("=" * 50)
    print(f"mAP50:      {metrics.box.map50:.4f}")
    print(f"mAP50-95:   {metrics.box.map:.4f}")
    print(f"Precision:  {metrics.box.mp:.4f}")
    print(f"Recall:     {metrics.box.mr:.4f}")
    print("=" * 50)

if __name__ == "__main__":
    main()