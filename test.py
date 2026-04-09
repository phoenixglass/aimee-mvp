import os
from aimee_classifier import AimeeClassifier

# 1. Print current working directory
print(f"Current directory: {os.getcwd()}")

# 2. List all files to verify
print("Files in directory:")
for f in os.listdir():
    print(f" - {f}")

# 3. Initialize classifier WITH ERROR HANDLING
try:
    print("\nInitializing classifier...")
    classifier = AimeeClassifier("aimee_training_data_tagged.json")
    
    # 4. Test classification
    test_phrases = [
        "Need 5 bottles delivered tomorrow",
        "What pairs with seafood?",
        "Order more Chardonnay"
    ]
    
    for phrase in test_phrases:
        result = classifier.classify(phrase)
        print(f"\nInput: '{phrase}'")
        print(f"Intent: {result['intent']}")
        print(f"Confidence: {result['match_score']:.2f}")
        
except Exception as e:
    print(f"\nERROR: {str(e)}")
    print("Troubleshooting tips:")
    print("1. Make sure the JSON file isn't open in another program")
    print("2. Check the JSON syntax is valid")
    print("3. Try moving the file to C:\\temp\\ and updating the path")