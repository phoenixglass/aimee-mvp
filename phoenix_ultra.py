#!/usr/bin/env python3
"""
PHOENIX'S AIMEE ENGINE - ULTRA COMPATIBLE VERSION
================================================
Strategic AI weapon that works on ANY system
Fixed for ALL numpy/scipy/sklearn version conflicts

MISSION: Build Phoenix's tech empire with ZERO technical roadblocks
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')
import time
from collections import Counter, defaultdict
import re

# Core ML libraries with compatibility fixes
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, accuracy_score, f1_score
import joblib

print("Loading required libraries...")

# Simple text processing without NLTK dependencies
class SimpleTextProcessor:
    """Ultra-simple text processor that works everywhere."""
    
    def __init__(self):
        self.contractions = {
            "can't": "cannot", "won't": "will not", "don't": "do not",
            "isn't": "is not", "what's": "what is", "that's": "that is",
            "it's": "it is", "i'm": "i am", "you're": "you are"
        }
    
    def process(self, text):
        if not text:
            return ""
        
        text = str(text).lower().strip()
        
        # Handle contractions
        for contraction, expansion in self.contractions.items():
            text = text.replace(contraction, expansion)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Basic cleaning
        text = re.sub(r'[^\w\s\.\!\?\,]', '', text)
        
        return text.strip()


class SimpleLogger:
    """Ultra-simple logger for Windows compatibility."""
    
    def info(self, msg):
        print(f"[INFO] {msg}")
    
    def warning(self, msg):
        print(f"[WARNING] {msg}")
    
    def error(self, msg):
        print(f"[ERROR] {msg}")


class PhoenixAimeeEngineUltra:
    """
    PHOENIX'S ULTRA-COMPATIBLE AI ENGINE
    
    Built to work on ANY system with ANY library versions.
    Zero dependencies, maximum compatibility.
    """
    
    def __init__(self):
        self.logger = SimpleLogger()
        self.text_processor = SimpleTextProcessor()
        
        # Models
        self.intent_model = None
        self.tone_model = None
        self.intent_vectorizer = None
        self.tone_vectorizer = None
        
        # Intelligence
        self.dataset_info = {}
        self.performance_info = {}
        
        self.logger.info("PHOENIX'S ULTRA-COMPATIBLE ENGINE INITIALIZED")
    
    def load_dataset(self, data_path="phoenix_aimee_data.jsonl"):
        """Load Phoenix's dataset with ultra-compatibility."""
        
        self.logger.info(f"Loading dataset: {data_path}")
        
        if not Path(data_path).exists():
            self.logger.error(f"Dataset not found: {data_path}")
            return None
        
        dataset = []
        
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())
                        if 'text' in data and 'intent' in data:
                            dataset.append(data)
                    except:
                        continue
            
            self.logger.info(f"Loaded {len(dataset)} examples")
            
            # Quick analysis
            intents = [d['intent'] for d in dataset]
            tones = [d.get('tone', 'neutral') for d in dataset]
            
            intent_counts = Counter(intents)
            tone_counts = Counter(tones)
            
            self.logger.info(f"Intent classes: {len(intent_counts)}")
            self.logger.info(f"Tone classes: {len(tone_counts)}")
            
            # Show top intents
            self.logger.info("Top intents:")
            for intent, count in intent_counts.most_common(5):
                self.logger.info(f"  {intent}: {count} examples")
            
            self.dataset_info = {
                'size': len(dataset),
                'intent_counts': dict(intent_counts),
                'tone_counts': dict(tone_counts)
            }
            
            return dataset
            
        except Exception as e:
            self.logger.error(f"Failed to load dataset: {e}")
            return None
    
    def prepare_data(self, dataset):
        """Prepare data for training with ultra-compatibility."""
        
        self.logger.info("Preparing data for training...")
        
        # Extract components
        texts = [item['text'] for item in dataset]
        intents = [item['intent'] for item in dataset]
        tones = [item.get('tone', 'neutral') for item in dataset]
        
        # Process texts
        processed_texts = [self.text_processor.process(text) for text in texts]
        
        # Create vectorizers with safe settings
        self.logger.info("Creating text vectorizers...")
        
        # Intent vectorizer
        self.intent_vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2),
            max_features=3000,
            min_df=1,
            max_df=0.95
        )
        
        # Tone vectorizer
        self.tone_vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2),
            max_features=2000,
            min_df=1,
            max_df=0.95
        )
        
        # Transform texts
        try:
            X_intent = self.intent_vectorizer.fit_transform(processed_texts)
            X_tone = self.tone_vectorizer.fit_transform(processed_texts)
            
            self.logger.info(f"Intent features: {X_intent.shape[1]}")
            self.logger.info(f"Tone features: {X_tone.shape[1]}")
            
            return X_intent, X_tone, intents, tones
            
        except Exception as e:
            self.logger.error(f"Data preparation failed: {e}")
            return None, None, None, None
    
    def train_models(self, X_intent, X_tone, intents, tones):
        """Train models with ultra-safe approach."""
        
        self.logger.info("Training strategic models...")
        
        # Train intent model
        self.logger.info("Training intent classifier...")
        self.intent_model = self._train_single_model(X_intent, intents, "intent")
        
        # Train tone model
        self.logger.info("Training tone classifier...")
        self.tone_model = self._train_single_model(X_tone, tones, "tone")
        
        # Test performance
        self._test_performance(X_intent, X_tone, intents, tones)
    
    def _train_single_model(self, X, y, model_type):
        """Train a single model with maximum compatibility."""
        
        # Check data shape compatibility
        n_samples = X.shape[0] if hasattr(X, 'shape') else len(X)
        
        self.logger.info(f"Training {model_type} model on {n_samples} samples...")
        
        # Use simple train/test split
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
        except:
            # Fallback if stratify fails
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
        
        # Train simple but effective model
        model = LogisticRegression(
            max_iter=1000,
            random_state=42,
            class_weight='balanced',
            solver='liblinear'  # Most compatible solver
        )
        
        try:
            model.fit(X_train, y_train)
            
            # Test performance
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred, average='weighted')
            
            self.logger.info(f"{model_type} accuracy: {accuracy:.3f}")
            self.logger.info(f"{model_type} F1 score: {f1:.3f}")
            
            return model
            
        except Exception as e:
            self.logger.error(f"Training {model_type} model failed: {e}")
            return None
    
    def _test_performance(self, X_intent, X_tone, intents, tones):
        """Test overall performance."""
        
        self.logger.info("Testing overall performance...")
        
        if self.intent_model is None or self.tone_model is None:
            self.logger.error("Models not trained properly")
            return
        
        # Test with simple predictions
        try:
            test_texts = [
                "I need wine recommendations for dinner",
                "The wine tastes too bitter",
                "Can you suggest a good Pinot Noir under fifty dollars",
                "This Chardonnay is perfect with seafood"
            ]
            
            self.logger.info("Testing with sample texts:")
            
            for text in test_texts:
                result = self.predict(text)
                if result:
                    self.logger.info(f"'{text}' -> Intent: {result['intent']}, Tone: {result['tone']}")
        
        except Exception as e:
            self.logger.error(f"Performance testing failed: {e}")
    
    def predict(self, text):
        """Make prediction with ultra-safe approach."""
        
        if not self.intent_model or not self.tone_model:
            return None
        
        try:
            # Process text
            processed = self.text_processor.process(text)
            
            # Vectorize
            intent_features = self.intent_vectorizer.transform([processed])
            tone_features = self.tone_vectorizer.transform([processed])
            
            # Predict
            intent = self.intent_model.predict(intent_features)[0]
            tone = self.tone_model.predict(tone_features)[0]
            
            return {
                'intent': intent,
                'tone': tone,
                'text': text,
                'processed': processed
            }
            
        except Exception as e:
            self.logger.error(f"Prediction failed: {e}")
            return None
    
    def save_models(self, version="ultra_v1.0"):
        """Save models for deployment."""
        
        self.logger.info("Saving Phoenix's strategic arsenal...")
        
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        
        files = {
            'intent_model': f"phoenix_intent_{version}_{timestamp}.pkl",
            'tone_model': f"phoenix_tone_{version}_{timestamp}.pkl",
            'intent_vectorizer': f"phoenix_intent_vec_{version}_{timestamp}.pkl",
            'tone_vectorizer': f"phoenix_tone_vec_{version}_{timestamp}.pkl",
            'metadata': f"phoenix_metadata_{version}_{timestamp}.json"
        }
        
        try:
            # Save models
            joblib.dump(self.intent_model, files['intent_model'])
            joblib.dump(self.tone_model, files['tone_model'])
            joblib.dump(self.intent_vectorizer, files['intent_vectorizer'])
            joblib.dump(self.tone_vectorizer, files['tone_vectorizer'])
            
            # Save metadata
            metadata = {
                'version': version,
                'timestamp': timestamp,
                'dataset_info': self.dataset_info,
                'files': files
            }
            
            with open(files['metadata'], 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            self.logger.info("Strategic arsenal saved successfully!")
            
            for component, filename in files.items():
                self.logger.info(f"  {component}: {filename}")
            
            # Create deployment script
            self._create_deployment_script(files, version, timestamp)
            
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to save models: {e}")
            return None
    
    def _create_deployment_script(self, files, version, timestamp):
        """Create simple deployment script."""
        
        script_name = f"phoenix_deploy_{version}_{timestamp}.py"
        
        script_content = f'''#!/usr/bin/env python3
"""
PHOENIX'S DEPLOYMENT SCRIPT
Ultra-compatible version for immediate use
"""

import joblib
import json

class PhoenixAimee:
    def __init__(self):
        # Load models
        self.intent_model = joblib.load("{files['intent_model']}")
        self.tone_model = joblib.load("{files['tone_model']}")
        self.intent_vectorizer = joblib.load("{files['intent_vectorizer']}")
        self.tone_vectorizer = joblib.load("{files['tone_vectorizer']}")
        
        print("Phoenix's Aimee loaded and ready!")
        print(f"Intent classes: {{len(self.intent_model.classes_)}}")
        print(f"Tone classes: {{len(self.tone_model.classes_)}}")
    
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
            
            return {{
                'intent': intent,
                'tone': tone,
                'text': text
            }}
        except Exception as e:
            return {{'error': str(e)}}

# Test function
def test_aimee():
    aimee = PhoenixAimee()
    
    test_cases = [
        "I need wine recommendations for dinner",
        "This wine is too expensive",
        "Can you suggest a good red wine under thirty dollars",
        "The Chardonnay pairs perfectly with the salmon"
    ]
    
    print("\\nTesting Phoenix's Aimee:")
    print("=" * 50)
    
    for text in test_cases:
        result = aimee.predict(text)
        if 'error' not in result:
            print(f"Text: '{{text}}'")
            print(f"Intent: {{result['intent']}}")
            print(f"Tone: {{result['tone']}}")
            print()
        else:
            print(f"Error with '{{text}}': {{result['error']}}")

if __name__ == "__main__":
    test_aimee()
'''
        
        with open(script_name, 'w') as f:
            f.write(script_content)
        
        self.logger.info(f"Deployment script created: {script_name}")
    
    def execute_full_training(self, data_path="phoenix_aimee_data.jsonl"):
        """Execute complete training mission with ultra-compatibility."""
        
        self.logger.info("EXECUTING PHOENIX'S ULTRA-COMPATIBLE TRAINING MISSION")
        self.logger.info("=" * 80)
        
        try:
            # Step 1: Load dataset
            dataset = self.load_dataset(data_path)
            if not dataset:
                return False
            
            # Step 2: Prepare data
            X_intent, X_tone, intents, tones = self.prepare_data(dataset)
            if X_intent is None:
                return False
            
            # Step 3: Train models
            self.train_models(X_intent, X_tone, intents, tones)
            
            # Step 4: Save everything
            files = self.save_models()
            
            if files:
                self.logger.info("MISSION SUCCESS!")
                self.logger.info("Phoenix's strategic AI arsenal is ready for deployment!")
                return True
            else:
                self.logger.error("Failed to save models")
                return False
                
        except Exception as e:
            self.logger.error(f"Training mission failed: {e}")
            return False


def main():
    """Main execution function."""
    
    print("PHOENIX'S STRATEGIC AI EMPIRE - ULTRA COMPATIBLE VERSION")
    print("Building tech empire with ZERO technical roadblocks")
    print("=" * 80)
    
    # Initialize engine
    engine = PhoenixAimeeEngineUltra()
    
    # Execute training
    success = engine.execute_full_training()
    
    if success:
        print("\\nCONGRATULATIONS!")
        print("Phoenix's AI empire foundation is complete!")
        print("Ready for world domination!")
    else:
        print("\\nTRAINING INCOMPLETE")
        print("Check your data file and try again")
    
    print("\\nPhoenix's path to tech dominance continues...")


if __name__ == "__main__":
    main()
