import torch
import json
import os

# Точно такой же CRNN, как в твоём обучении
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


def load_charset(charset_path: str):
    with open(charset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    char2idx = data["char2idx"]
    idx2char = data["idx2char"]
    num_classes = len(char2idx)
    return char2idx, idx2char, num_classes


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
weights_path = os.path.join(BASE_DIR, "models", "CRNN.pth")  # <-- твоё имя файла
charset_path = os.path.join(BASE_DIR, "data", "charset.json")

print("1. Загружаем charset...")
_, _, num_classes = load_charset(charset_path)
print(f"   num_classes (с blank) = {num_classes}")

print("2. Создаём модель с той же архитектурой...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = CRNN(num_classes=num_classes).to(device)
model.eval()

print("3. Пробуем загрузить веса из CRNN.pth...")
state_dict = torch.load(weights_path, map_location=device)
if isinstance(state_dict, dict) and "model_state_dict" in state_dict:
    state_dict = state_dict["model_state_dict"]

model.load_state_dict(state_dict)
print("✅ Веса загружены без ошибок!")

print("4. Прогоняем один тестовый тензор (проверка forward)...")
dummy_input = torch.randn(1, 1, 64, 384).to(device)
with torch.no_grad():
    out = model(dummy_input)
print(f"✅ Forward прошёл. Выход: {out.shape}")
print("🎉 Тест 1 пройден: архитектура и веса совместимы.")