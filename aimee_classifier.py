import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

class AimeeClassifier:
    def __init__(self, data_file: str, threshold: float = 0.1):
        self.data_file = data_file
        self.threshold = threshold
        self.model = self._train_model()

    def _load_training_data(self):
        with open(self.data_file) as f:
            data = json.load(f)
        return data['training_examples']

    def _train_model(self):
        data = self._load_training_data()
        texts = [item['text'] for item in data]
        labels = [item['intent'] for item in data]
        
        model = Pipeline([
            ('tfidf', TfidfVectorizer()),
            ('clf', MultinomialNB())
        ])
        model.fit(texts, labels)
        return model

    def classify(self, text: str):
        probas = self.model.predict_proba([text])[0]
        best_idx = np.argmax(probas)
        return {
            "intent": self.model.classes_[best_idx],
            "match_score": float(probas[best_idx]),
            "entities": {}
        }

    def get_stats(self):
        data = self._load_training_data()
        return {
            "training_samples": len(data),
            "intent_counts": {
                "add_to_order": sum(1 for x in data if x['intent'] == "add_to_order"),
                # Add other intents here
            }
        }