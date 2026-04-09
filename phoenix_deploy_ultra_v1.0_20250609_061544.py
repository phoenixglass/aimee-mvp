#!/usr/bin/env python3
"""
PHOENIX'S DEPLOYMENT SCRIPT
Ultra-compatible version for immediate use
"""

import joblib
import json

class PhoenixAimee:
    def __init__(self):
        # Load models
        self.intent_model = joblib.load("phoenix_intent_ultra_v1.0_20250609_061544.pkl")
        self.tone_model = joblib.load("phoenix_tone_ultra_v1.0_20250609_061544.pkl")
        self.intent_vectorizer = joblib.load("phoenix_intent_vec_ultra_v1.0_20250609_061544.pkl")
        self.tone_vectorizer = joblib.load("phoenix_tone_vec_ultra_v1.0_20250609_061544.pkl")
        
        print("Phoenix's Aimee loaded and ready!")
        print(f"Intent classes: {len(self.intent_model.classes_)}")
        print(f"Tone classes: {len(self.tone_model.classes_)}")
    
    def predict(self, text):
        """Predict intent and tone for text."""
        try:
            # Simple text processing
            processed = text.lower().strip()
            
            # Vectorize
            intent_features = self.intent_vectorizer.transform([processed])
            tone_features = self.tone_vectorizer.transform([processed])
            
            # Predict
            intent = self.intent_model.predict(intent_features)[0]
            tone = self.tone_model.predict(tone_features)[0]
            
            return {
                'intent': intent,
                'tone': tone,
                'text': text
            }
        except Exception as e:
            return {'error': str(e)}

# Test function
def test_aimee():
    aimee = PhoenixAimee()
    
    test_cases = [
        "I need wine recommendations for dinner",
        "This wine is too expensive",
        "Can you suggest a good red wine under thirty dollars",
        "The Chardonnay pairs perfectly with the salmon"
    ]
    
    print("\nTesting Phoenix's Aimee:")
    print("=" * 50)
    
    for text in test_cases:
        result = aimee.predict(text)
        if 'error' not in result:
            print(f"Text: '{text}'")
            print(f"Intent: {result['intent']}")
            print(f"Tone: {result['tone']}")
            print()
        else:
            print(f"Error with '{text}': {result['error']}")

if __name__ == "__main__":
    test_aimee()
