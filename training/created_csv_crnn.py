import pandas as pd
from pathlib import Path
import random

# === Настройки ===
LABELS_CSV = "data/labels_final.csv"   # <-- путь исправлен
VAL_RATIO = 0.1
RANDOM_SEED = 42

random.seed(RANDOM_SEED)

df = pd.read_csv(LABELS_CSV)
print(f"Всего в labels_final.csv: {len(df)}")

df["exists"] = df["path"].apply(lambda p: Path(p).exists())
print(f"Существующих файлов: {df['exists'].sum()}")

df = df[df["exists"]].drop(columns=["exists"]).reset_index(drop=True)

indices = list(range(len(df)))
random.shuffle(indices)

val_size = int(len(df) * VAL_RATIO)
val_idx = set(indices[:val_size])

train_df = df.iloc[[i for i in range(len(df)) if i not in val_idx]].reset_index(drop=True)
val_df   = df.iloc[list(val_idx)].reset_index(drop=True)

train_df.to_csv("train.csv", index=False)
val_df.to_csv("val.csv", index=False)

print(f"Создан train.csv: {len(train_df)} примеров")
print(f"Создан val.csv:   {len(val_df)} примеров")
print("Готово!")