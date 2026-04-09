import json
with open("aimee_training_data_tagged.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    print(f"✅ Loaded {len(data)} clips")
    for k, v in list(data.items())[:3]:  # Print first 3
        print(f"{k}: {v}")
debug
