# Merge multiple JSON lists (assumes both are lists of dicts)
import json

with open("aimee_labeled_dataset.json", "r", encoding="utf-8") as f1, \
     open("aimee_synthetic_dataset_300.json", "r", encoding="utf-8") as f2:
    data1 = json.load(f1)
    data2 = json.load(f2)

merged = data1 + data2
print(f"Merged dataset size: {len(merged)}")

with open("aimee_full_training_set.json", "w", encoding="utf-8") as f_out:
    json.dump(merged, f_out, ensure_ascii=False, indent=2)
