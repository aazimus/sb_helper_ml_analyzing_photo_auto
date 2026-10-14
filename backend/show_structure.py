import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Исключаем очень тяжёлые папки, если хочешь, чтобы вывод не был километровым.
# Если хочешь АБСОЛЮТНО ВСЁ — поставь EXCLUDE = []
EXCLUDE = ["training", ".venv"]  # .venv — виртуальное окружение, training — там могут быть тысячи файлов

def get_tree(root_path, prefix="", is_last=True, depth=0, max_depth=3):
    """Рекурсивно строит дерево папок."""
    try:
        entries = sorted(os.listdir(root_path))
    except PermissionError:
        return

    for i, entry in enumerate(entries):
        path = os.path.join(root_path, entry)
        is_file = not os.path.isdir(path)
        
        # Пропускаем исключённые папки
        if not is_file and entry in EXCLUDE:
            print(prefix + ("└── " if is_last else "├── ") + f"[{entry}/] (skipped)")
            continue

        connector = "└── " if is_last else "├── "
        print(prefix + connector + entry + ("/" if not is_file else ""))

        # Рекурсия только для папок и если не превышена глубина
        if not is_file and depth < max_depth:
            new_prefix = prefix + ("    " if is_last else "│   ")
            sub_is_last = (i == len(entries) - 1)
            get_tree(path, new_prefix, sub_is_last, depth + 1, max_depth)

print("📂 Полная структура проекта (Django + YOLO + CRNN)")
print("=" * 80)
get_tree(BASE_DIR, prefix="", is_last=True, depth=0, max_depth=3)
print("=" * 80)
print("✅ Готово. Папки training и .venv пропущены, чтобы вывод был читаемым.")