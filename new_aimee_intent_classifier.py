#!/usr/bin/env python3
"""
Aimee Intent Classifier Training Pipeline
=========================================
Train a text classifier to predict user intents for wine sales reps.

Author: AI Assistant
Date: June 2025
"""

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# Core ML libraries
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report, 
    confusion_matrix, 
    accuracy_score,
    f1_score
)
import joblib


class AimeeIntentClassifier:
    """Complete intent classification pipeline for Aimee voice AI."""
    
    def __init__(self, data_path="aimee_clean_training_data.jsonl"):
        self.data_path = data_path
        self.vectorizer = None
        self.classifier = None
        self.class_distribution = None
        
    def load_jsonl(self, path):
        """Load JSONL dataset."""
        data = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data.append(json.loads(line.strip()))
                    except json.JSONDecodeError as e:
                        print(f"Warning: Skipping malformed JSON on line {line_num}: {e}")
            
            print(f"✅ Loaded {len(data)} samples from {path}")
            return data
            
        except FileNotFoundError:
            print(f"❌ Error: File '{path}' not found.")
            print("Creating sample data for demonstration...")
            return self._create_sample_data()
    
    def _create_sample_data(self):
        """Create sample training data for demonstration."""
        sample_data = [
            {"text": "Did we ever ship that Barolo to Le Bella's?", "intent": "check_shipment_status"},
            {"text": "Can you send me some samples of that Pinot?", "intent": "request_samples"},
            {"text": "What's the price on the 2019 Cabernet?", "intent": "price_inquiry"},
            {"text": "Send an email to John about the wine tasting", "intent": "send_email"},
            {"text": "Do we have any Chardonnay in stock?", "intent": "check_inventory"},
            {"text": "I need a wine recommendation for seafood", "intent": "product_recommendation"},
            {"text": "Schedule a meeting with the vineyard owner", "intent": "schedule_meeting"},
            {"text": "What's the status of order #12345?", "intent": "check_order_status"},
            {"text": "Can you recommend a good red wine under $50?", "intent": "product_recommendation"},
            {"text": "Has the Merlot shipment arrived yet?", "intent": "check_shipment_status"},
            {"text": "Send the wine list to the restaurant", "intent": "send_email"},
            {"text": "How much Pinot Grigio do we have left?", "intent": "check_inventory"},
            {"text": "I want to order 12 bottles of Rosé", "intent": "place_order"},
            {"text": "What goes well with lamb?", "intent": "product_recommendation"},
            {"text": "Email the invoice to the customer", "intent": "send_email"},
            {"text": "Track my wine delivery", "intent": "check_shipment_status"},
            {"text": "Book a wine tasting for next Friday", "intent": "schedule_meeting"},
            {"text": "What's our best selling Sauvignon Blanc?", "intent": "product_recommendation"},
            {"text": "Send samples of the new vintage", "intent": "request_samples"},
            {"text": "Check if order 67890 has been processed", "intent": "check_order_status"}
        ]
        
        # Save sample data
        with open("aimee_clean_training_data.jsonl", 'w', encoding='utf-8') as f:
            for item in sample_data:
                f.write(json.dumps(item) + '\n')
        
        print("📝 Created sample training data file: aimee_clean_training_data.jsonl")
        return sample_data
    
    def analyze_dataset(self, dataset):
        """Analyze and display dataset statistics."""
        texts = [d["text"] for d in dataset]
        labels = [d["intent"] for d in dataset]
        
        print("\n📊 Dataset Analysis")
        print("=" * 50)
        print(f"Total samples: {len(dataset)}")
        print(f"Unique intents: {len(set(labels))}")
        
        # Class distribution
        self.class_distribution = Counter(labels)
        print(f"\nClass Distribution:")
        for intent, count in self.class_distribution.most_common():
            print(f"  {intent}: {count} samples ({count/len(labels)*100:.1f}%)")
        
        # Text length statistics
        text_lengths = [len(text.split()) for text in texts]
        print(f"\nText Length Statistics:")
        print(f"  Average words per text: {np.mean(text_lengths):.1f}")
        print(f"  Min/Max words: {min(text_lengths)}/{max(text_lengths)}")
        
        return texts, labels
    
    def preprocess_and_vectorize(self, texts):
        """Create TF-IDF vectorizer and transform texts."""
        print("\n🧹 Preprocessing and Vectorization")
        print("=" * 50)
        
        # Initialize TF-IDF vectorizer with wine-specific considerations
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2),  # Unigrams and bigrams
            max_features=5000,   # Limit features to prevent overfitting
            min_df=1,           # Keep rare terms (small dataset)
            max_df=0.95         # Remove very common terms
        )
        
        X = self.vectorizer.fit_transform(texts)
        
        print(f"✅ Created {X.shape[1]} features from {X.shape[0]} texts")
        print(f"Vocabulary size: {len(self.vectorizer.vocabulary_)}")
        
        return X
    
    def train_models(self, X, y):
        """Train and compare multiple classifiers."""
        print("\n🤖 Model Training and Selection")
        print("=" * 50)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )
        
        print(f"Training set: {X_train.shape[0]} samples")
        print(f"Test set: {X_test.shape[0]} samples")
        
        # Define models to compare
        models = {
            'Logistic Regression': LogisticRegression(
                max_iter=1000, 
                class_weight='balanced',
                random_state=42
            ),
            'Random Forest': RandomForestClassifier(
                n_estimators=100,
                class_weight='balanced',
                random_state=42
            )
        }
        
        # Train and evaluate models
        results = {}
        for name, model in models.items():
            print(f"\nTraining {name}...")
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train, y_train, cv=3, scoring='f1_weighted')
            
            # Train on full training set
            model.fit(X_train, y_train)
            
            # Evaluate on test set
            test_pred = model.predict(X_test)
            test_f1 = f1_score(y_test, test_pred, average='weighted')
            test_acc = accuracy_score(y_test, test_pred)
            
            results[name] = {
                'model': model,
                'cv_f1_mean': cv_scores.mean(),
                'cv_f1_std': cv_scores.std(),
                'test_f1': test_f1,
                'test_accuracy': test_acc,
                'test_pred': test_pred
            }
            
            print(f"  CV F1: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
            print(f"  Test F1: {test_f1:.3f}")
            print(f"  Test Accuracy: {test_acc:.3f}")
        
        # Select best model
        best_model_name = max(results.keys(), key=lambda k: results[k]['test_f1'])
        self.classifier = results[best_model_name]['model']
        
        print(f"\n🏆 Best model: {best_model_name}")
        
        return X_test, y_test, results[best_model_name]['test_pred']
    
    def evaluate_model(self, X_test, y_test, y_pred):
        """Generate comprehensive evaluation report."""
        print("\n📊 Model Evaluation")
        print("=" * 50)
        
        # Classification report
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, digits=3))
        
        # Confusion Matrix
        plt.figure(figsize=(10, 8))
        cm = confusion_matrix(y_test, y_pred, labels=self.classifier.classes_)
        
        # Create DataFrame for better visualization
        cm_df = pd.DataFrame(cm, index=self.classifier.classes_, columns=self.classifier.classes_)
        
        sns.heatmap(cm_df, annot=True, fmt='d', cmap='Blues', cbar_kws={'label': 'Count'})
        plt.title("Confusion Matrix - Intent Classification")
        plt.ylabel("True Intent")
        plt.xlabel("Predicted Intent")
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        plt.savefig('aimee_confusion_matrix.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # Feature importance (if available)
        if hasattr(self.classifier, 'coef_'):
            self._analyze_feature_importance()
    
    def _analyze_feature_importance(self):
        """Analyze and display important features for each intent."""
        print("\n🔍 Feature Importance Analysis")
        print("=" * 50)
        
        feature_names = self.vectorizer.get_feature_names_out()
        
        # For each class, show top positive and negative features
        for i, intent in enumerate(self.classifier.classes_):
            coef = self.classifier.coef_[i]
            
            # Get top positive features
            top_pos_idx = coef.argsort()[-5:][::-1]
            top_pos_features = [feature_names[idx] for idx in top_pos_idx]
            top_pos_scores = [coef[idx] for idx in top_pos_idx]
            
            print(f"\n{intent}:")
            print("  Top predictive features:")
            for feature, score in zip(top_pos_features, top_pos_scores):
                print(f"    {feature}: {score:.3f}")
    
    def save_models(self):
        """Save trained models for deployment."""
        print("\n💾 Saving Models")
        print("=" * 50)
        
        # Save classifier
        joblib.dump(self.classifier, "aimee_intent_model.pkl")
        print("✅ Saved classifier: aimee_intent_model.pkl")
        
        # Save vectorizer
        joblib.dump(self.vectorizer, "aimee_vectorizer.pkl")
        print("✅ Saved vectorizer: aimee_vectorizer.pkl")
        
        # Save metadata
        metadata = {
            'class_distribution': dict(self.class_distribution),
            'classes': list(self.classifier.classes_),
            'feature_count': len(self.vectorizer.vocabulary_),
            'model_type': type(self.classifier).__name__
        }
        
        with open("aimee_model_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        print("✅ Saved metadata: aimee_model_metadata.json")
    
    def predict_intent(self, text):
        """Predict intent for new text input."""
        if not self.classifier or not self.vectorizer:
            raise ValueError("Model not trained. Call train() first.")
        
        # Vectorize input
        vec = self.vectorizer.transform([text])
        
        # Get prediction and probability
        intent = self.classifier.predict(vec)[0]
        probabilities = self.classifier.predict_proba(vec)[0]
        
        # Get confidence scores for all classes
        class_probs = dict(zip(self.classifier.classes_, probabilities))
        
        return {
            'intent': intent,
            'confidence': max(probabilities),
            'all_probabilities': class_probs
        }
    
    def test_predictions(self):
        """Test the model with sample inputs."""
        print("\n🧪 Testing Predictions")
        print("=" * 50)
        
        test_texts = [
            "Can you send me some samples of that Pinot?",
            "What's the shipping status of my order?",
            "I need a wine recommendation for dinner",
            "Send an email to the client about pricing",
            "Do we have any Merlot in stock?",
            "Schedule a meeting with the distributor"
        ]
        
        for text in test_texts:
            result = self.predict_intent(text)
            print(f"\nText: '{text}'")
            print(f"Predicted Intent: {result['intent']}")
            print(f"Confidence: {result['confidence']:.3f}")
            
            # Show top 3 predictions
            sorted_probs = sorted(result['all_probabilities'].items(), 
                                key=lambda x: x[1], reverse=True)[:3]
            print("Top 3 predictions:")
            for intent, prob in sorted_probs:
                print(f"  {intent}: {prob:.3f}")
    
    def train(self):
        """Complete training pipeline."""
        print("🚀 Starting Aimee Intent Classifier Training")
        print("=" * 60)
        
        # Load data
        dataset = self.load_jsonl(self.data_path)
        if not dataset:
            return
        
        # Analyze dataset
        texts, labels = self.analyze_dataset(dataset)
        
        # Preprocess and vectorize
        X = self.preprocess_and_vectorize(texts)
        
        # Train models
        X_test, y_test, y_pred = self.train_models(X, labels)
        
        # Evaluate
        self.evaluate_model(X_test, y_test, y_pred)
        
        # Save models
        self.save_models()
        
        # Test predictions
        self.test_predictions()
        
        print("\n🎉 Training Complete!")
        print("=" * 60)
        print("Deliverables created:")
        print("  📦 aimee_intent_model.pkl - Trained classifier")
        print("  📦 aimee_vectorizer.pkl - Text preprocessing pipeline")
        print("  📊 aimee_confusion_matrix.png - Evaluation visualization")
        print("  📄 aimee_model_metadata.json - Model information")


def load_and_predict(text, model_path="aimee_intent_model.pkl", 
                    vectorizer_path="aimee_vectorizer.pkl"):
    """Utility function to load saved models and make predictions."""
    try:
        clf = joblib.load(model_path)
        vectorizer = joblib.load(vectorizer_path)
        
        vec = vectorizer.transform([text])
        intent = clf.predict(vec)[0]
        probabilities = clf.predict_proba(vec)[0]
        confidence = max(probabilities)
        
        return {
            'intent': intent,
            'confidence': confidence,
            'text': text
        }
    except FileNotFoundError as e:
        print(f"Error loading models: {e}")
        return None


if __name__ == "__main__":
    # Initialize and train the classifier
    classifier = AimeeIntentClassifier()
    classifier.train()
    
    print("\n" + "="*60)
    print("🍷 Aimee Intent Classifier Ready for Deployment!")
    print("="*60)
    
    # Interactive testing
    print("\nTry it out! Enter some wine-related queries:")
    print("(Press Enter without text to exit)")
    
    while True:
        user_input = input("\n🎤 Enter query: ").strip()
        if not user_input:
            break
            
        try:
            result = classifier.predict_intent(user_input)
            print(f"🎯 Intent: {result['intent']}")
            print(f"📊 Confidence: {result['confidence']:.1%}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n👋 Thanks for using Aimee Intent Classifier!")