import json

with open("wine_subset.json", "r", encoding="utf-8") as f:
    wine_data = json.load(f)

converted_data = []

# Navigate into the 'taste_profiles' block
taste_profiles = wine_data.get("taste_profiles", {})

for entry in taste_profiles.values():
    review_text = entry.get("review", "").strip()
    if review_text:
        converted_data.append({"data": {"text": review_text}})

with open("wine_for_labelstudio.json", "w", encoding="utf-8") as f_out:
    json.dump(converted_data, f_out, ensure_ascii=False, indent=2)

print(f"✅ Converted {len(converted_data)} reviews.")
