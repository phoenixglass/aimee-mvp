import json

with open("wine_subset.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Type: {type(data)}")
print(f"Top-level keys: {list(data.keys())[:5]}")
sample_key = list(data.keys())[0]
print(f"Sample item:\n{json.dumps(data[sample_key], indent=2, ensure_ascii=False)}")
