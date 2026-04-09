import json

with open("wine_intelligence_data.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

taste_profiles = raw_data.get("taste_profiles", {})

with open("aimee_reviews.jsonl", "w", encoding="utf-8") as out:
    count = 0
    for value in taste_profiles.values():
        review = value.get("review", "").strip()
        if review:
            out.write(json.dumps({"text": review}) + "\n")
            count += 1

print(f"✅ Extracted {count} reviews into aimee_reviews.jsonl")