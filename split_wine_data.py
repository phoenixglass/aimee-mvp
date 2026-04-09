import json

with open("wine_intelligence_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Slice the first 5000 entries under "taste_profiles"
subset = dict(list(data["taste_profiles"].items())[:5000])

with open("wine_subset.json", "w", encoding="utf-8") as f:
    json.dump({"taste_profiles": subset}, f, indent=2)
