import pandas as pd
import random

class AimeeWinePromptBuilder:
    def __init__(self, csv_path, n_examples=5):
        self.data = pd.read_csv(csv_path)
        self.n_examples = n_examples

    def sample_prompts(self):
        sampled = self.data.sample(self.n_examples)
        qa_pairs = []

        for _, row in sampled.iterrows():
            question = f"Recommend a {row['grape']} from {row['country']} under ${int(row['price']) + 5}."
            answer = (
                f"Try a {row['year']} {row['grape']} from {row['region'].strip()}, {row['country']}.\n"
                f"It’s rated {row['rating']}, priced at ${row['price']:.2f}.\n"
                f"User review: “{row['review']}”"
            )
            qa_pairs.append({"Q": question, "A": answer})

        return qa_pairs

    def format_prompt_block(self, user_question):
        examples = self.sample_prompts()
        formatted = ""

        for pair in examples:
            formatted += f"Q: {pair['Q']}\nA: {pair['A']}\n\n"

        formatted += f"Q: {user_question}\nA:"
        return formatted

# Example Usage:
# builder = AimeeWinePromptBuilder("cleaned_wine_dataset_for_aimee.csv", n_examples=3)
# prompt = builder.format_prompt_block("Recommend a bold red under $25 for a night by the fire.")
# print(prompt)
