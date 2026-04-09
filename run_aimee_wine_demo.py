from aimee_prompt_generator import AimeeWinePromptBuilder

def main():
    # Path to your cleaned dataset CSV
    dataset_path = "cleaned_wine_dataset_for_aimee.csv"
    
    # Initialize the prompt builder with 3 few-shot examples
    builder = AimeeWinePromptBuilder(dataset_path, n_examples=3)

    # Example user query
    user_question = "Recommend a bold Italian red under $30 for a date night."

    # Build full prompt
    full_prompt = builder.format_prompt_block(user_question)

    # Print result
    print("\n========== Aimee Prompt Preview ==========\n")
    print(full_prompt)

if __name__ == "__main__":
    main()
