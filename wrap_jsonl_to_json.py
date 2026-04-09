import json

input_file = "aimee_synthetic_dataset_tone_varied.jsonl"
output_file = "aimee_synthetic_wrapped_with_tone.json"

with open(input_file, "r", encoding="utf-8") as f_in:
    lines = [json.loads(line.strip()) for line in f_in if line.strip()]

with open(output_file, "w", encoding="utf-8") as f_out:
    json.dump(lines, f_out, ensure_ascii=False, indent=2)

print(f"✅ Wrapped {len(lines)} entries into {output_file}")
