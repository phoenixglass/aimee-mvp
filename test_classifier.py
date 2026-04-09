from aimee_classifier import AimeeClassifier

# 1. Initialize the classifier with your training data
print("Loading classifier...")
classifier = AimeeClassifier("aimee_training_data_tagged.json")

# 2. Test some sample queries
test_phrases = [
    "What wine pairs with fish?",
    "Order 3 bottles of Cabernet",
    "Check inventory for Chardonnay",
    "What's your best red wine?"
]

print("\nTesting classification:")
for phrase in test_phrases:
    result = classifier.classify(phrase)
    print(f"\nInput: '{phrase}'")
    print(f"Intent: {result['intent']}")
    print(f"Confidence: {result['match_score']:.2f}")
    print(f"Entities: {result['entities']}")

# 3. Show statistics
print("\nClassifier Stats:")
stats = classifier.get_stats()
for key, value in stats.items():
    print(f"{key:>18}: {value}")