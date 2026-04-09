import json

with open("aimee_labeled_reviews_v1.json", "r", encoding="utf-8") as f:
    data = json.load(f)

output = []

for item in data:
    try:
        text = item["data"]["text"]
        annotations = item["annotations"][0]["result"]
        intent = None
        tone = None
        entities = []

        for result in annotations:
            if result["from_name"] == "intent":
                intent = result["value"]["choices"][0]
            elif result["from_name"] == "tone":
                tone = result["value"]["choices"][0]
            elif result["type"] == "labels":
                entities.append({
                    "start": result["value"]["start"],
                    "end": result["value"]["end"],
                    "label": result["value"]["labels"][0]
                })

        output.append({
            "text": text,
            "intent": intent,
            "tone": tone,
            "entities": entities
        })
    except Exception as e:
        print("Skipping item due to error:", e)

with open("aimee_clean_training_data.jsonl", "w", encoding="utf-8") as f_out:
    for line in output:
        json.dump(line, f_out)
        f_out.write("\n")

print(f"✅ {len(output)} entries converted to aimee_clean_training_data.jsonl")
