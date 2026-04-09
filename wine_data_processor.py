# wine_data_processor.py
# Process JSONL wine review data for Aimee's intelligence system

import json
import re
from collections import defaultdict, Counter
from typing import List, Dict, Any
import pandas as pd

class WineDataProcessor:
    def __init__(self, jsonl_file_path: str):
        self.jsonl_file = jsonl_file_path
        self.wine_reviews = []
        self.taste_profiles = {}
        self.wine_descriptors = defaultdict(list)
        
    def load_wine_data(self):
        """Load wine reviews from JSONL file"""
        print("Loading wine review data...")
        
        with open(self.jsonl_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:  # Skip empty lines
                    try:
                        wine_record = json.loads(line)
                        if wine_record.get('review'):  # Only keep records with reviews
                            self.wine_reviews.append(wine_record)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing line {line_num}: {e}")
                        continue
        
        print(f"✅ Loaded {len(self.wine_reviews)} wine reviews")
        return self.wine_reviews
    
    def extract_taste_descriptors(self):
        """Extract taste descriptors from wine reviews"""
        print("Extracting taste descriptors...")
        
        # Common wine descriptors to look for
        taste_keywords = {
            'fruit': ['fruity', 'fruit', 'berry', 'blackberry', 'strawberry', 'cherry', 'plum', 
                     'apple', 'pear', 'peach', 'apricot', 'citrus', 'lemon', 'lime', 'grapefruit'],
            'earth': ['earthy', 'mineral', 'minerality', 'soil', 'stone', 'slate', 'chalk'],
            'wood': ['oak', 'oaky', 'vanilla', 'cedar', 'spice', 'spicy', 'smoke', 'smoky'],
            'body': ['light', 'medium', 'full', 'bold', 'delicate', 'robust', 'smooth', 'crisp'],
            'tannins': ['tannic', 'tannins', 'dry', 'astringent', 'grippy', 'silky', 'velvety'],
            'finish': ['finish', 'lingering', 'long', 'short', 'clean', 'persistent']
        }
        
        for wine in self.wine_reviews:
            review_text = wine['review'].lower()
            wine_id = wine['vintage_id']
            
            # Extract descriptors for each category
            wine_profile = {'vintage_id': wine_id, 'review': wine['review']}
            
            for category, keywords in taste_keywords.items():
                found_descriptors = []
                for keyword in keywords:
                    if keyword in review_text:
                        found_descriptors.append(keyword)
                wine_profile[category] = found_descriptors
            
            self.taste_profiles[wine_id] = wine_profile
        
        print(f"✅ Extracted taste profiles for {len(self.taste_profiles)} wines")
        return self.taste_profiles
    
    def create_wine_recommendations(self, customer_preference: str) -> List[Dict]:
        """Find wines matching customer taste preferences"""
        customer_pref_lower = customer_preference.lower()
        matching_wines = []
        
        for wine_id, profile in self.taste_profiles.items():
            score = 0
            matched_descriptors = []
            
            # Check each category for matches
            for category, descriptors in profile.items():
                if category in ['vintage_id', 'review']:
                    continue
                    
                for descriptor in descriptors:
                    if descriptor in customer_pref_lower:
                        score += 1
                        matched_descriptors.append(descriptor)
            
            # Also check the full review text
            if any(word in profile['review'].lower() for word in customer_pref_lower.split()):
                score += 0.5
            
            if score > 0:
                matching_wines.append({
                    'vintage_id': wine_id,
                    'score': score,
                    'matched_descriptors': matched_descriptors,
                    'review': profile['review'][:200] + "..." if len(profile['review']) > 200 else profile['review']
                })
        
        # Sort by relevance score
        matching_wines.sort(key=lambda x: x['score'], reverse=True)
        return matching_wines[:10]  # Top 10 matches
    
    def generate_training_data_for_aimee(self) -> List[Dict]:
        """Convert wine reviews into training examples for Aimee's classifier"""
        training_examples = []
        
        # Create training examples for different intents
        intent_templates = {
            "taste_preference_query": [
                "I like {descriptors} wines",
                "Do you have anything {descriptors}?",
                "I'm looking for something {descriptors}",
                "What {descriptors} wines do you recommend?"
            ],
            "wine_pairing_request": [
                "What wine goes with {food}?",
                "I need a wine for {food}",
                "Recommend a wine for {food}"
            ],
            "flavor_profile_inquiry": [
                "Tell me about {wine_type}",
                "What does {wine_type} taste like?",
                "Describe the flavor of {wine_type}"
            ]
        }
        
        # Extract common descriptors from reviews
        common_descriptors = []
        for profile in self.taste_profiles.values():
            for category, descriptors in profile.items():
                if category not in ['vintage_id', 'review'] and descriptors:
                    common_descriptors.extend(descriptors)
        
        descriptor_counts = Counter(common_descriptors)
        top_descriptors = [desc for desc, count in descriptor_counts.most_common(20)]
        
        # Generate examples
        for intent, templates in intent_templates.items():
            for template in templates:
                for descriptor in top_descriptors[:5]:  # Use top 5 descriptors
                    if "{descriptors}" in template:
                        text = template.replace("{descriptors}", descriptor)
                    elif "{wine_type}" in template:
                        text = template.replace("{wine_type}", f"{descriptor} wine")
                    elif "{food}" in template:
                        # Skip food templates for now
                        continue
                    else:
                        text = template
                    
                    training_examples.append({
                        "text": text,
                        "intent": intent,
                        "entities": {
                            "taste_descriptor": descriptor if "{descriptors}" in template else None
                        }
                    })
        
        return training_examples
    
    def export_for_aimee_integration(self, output_file: str = "wine_intelligence_data.json"):
        """Export processed data for integration with Aimee"""
        
        # Create comprehensive wine intelligence dataset
        wine_intelligence = {
            "taste_profiles": self.taste_profiles,
            "common_descriptors": self._get_common_descriptors(),
            "recommendation_engine": self._create_recommendation_mappings(),
            "training_examples": self.generate_training_data_for_aimee(),
            "stats": {
                "total_wines": len(self.wine_reviews),
                "wines_with_profiles": len(self.taste_profiles),
                "unique_descriptors": len(self._get_all_descriptors())
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(wine_intelligence, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Wine intelligence data exported to {output_file}")
        return wine_intelligence
    
    def _get_common_descriptors(self) -> Dict[str, List[str]]:
        """Get most common descriptors by category"""
        category_descriptors = defaultdict(list)
        
        for profile in self.taste_profiles.values():
            for category, descriptors in profile.items():
                if category not in ['vintage_id', 'review'] and descriptors:
                    category_descriptors[category].extend(descriptors)
        
        # Get top 10 for each category
        common_by_category = {}
        for category, descriptors in category_descriptors.items():
            descriptor_counts = Counter(descriptors)
            common_by_category[category] = [desc for desc, count in descriptor_counts.most_common(10)]
        
        return common_by_category
    
    def _get_all_descriptors(self) -> set:
        """Get all unique descriptors"""
        all_descriptors = set()
        for profile in self.taste_profiles.values():
            for category, descriptors in profile.items():
                if category not in ['vintage_id', 'review']:
                    all_descriptors.update(descriptors)
        return all_descriptors
    
    def _create_recommendation_mappings(self) -> Dict[str, List[int]]:
        """Create descriptor -> wine ID mappings for quick recommendations"""
        descriptor_to_wines = defaultdict(list)
        
        for wine_id, profile in self.taste_profiles.items():
            for category, descriptors in profile.items():
                if category not in ['vintage_id', 'review']:
                    for descriptor in descriptors:
                        descriptor_to_wines[descriptor].append(wine_id)
        
        # Convert to regular dict and limit to top wines per descriptor
        return {desc: wines[:20] for desc, wines in descriptor_to_wines.items()}

# Usage example and integration
def integrate_with_aimee(jsonl_file_path: str):
    """Main function to process wine data and integrate with Aimee"""
    
    # Step 1: Process the wine data
    processor = WineDataProcessor(jsonl_file_path)
    processor.load_wine_data()
    processor.extract_taste_descriptors()
    
    # Step 2: Export for Aimee integration
    wine_data = processor.export_for_aimee_integration()
    
    # Step 3: Demo the recommendation system
    print("\n=== WINE RECOMMENDATION DEMO ===")
    
    test_preferences = [
        "I like fruity and smooth wines",
        "Something bold and oaky",
        "Light and crisp white wine",
        "Full-bodied with vanilla notes"
    ]
    
    for preference in test_preferences:
        print(f"\nCustomer: '{preference}'")
        recommendations = processor.create_wine_recommendations(preference)
        
        if recommendations:
            print(f"🍷 Top recommendation (Score: {recommendations[0]['score']}):")
            print(f"   Wine ID: {recommendations[0]['vintage_id']}")
            print(f"   Matched: {', '.join(recommendations[0]['matched_descriptors'])}")
            print(f"   Review: {recommendations[0]['review']}")
        else:
            print("   No matching wines found")
    
    # Step 4: Show training data sample
    print(f"\n=== TRAINING DATA SAMPLE ===")
    training_examples = wine_data['training_examples'][:5]
    for example in training_examples:
        print(f"Text: '{example['text']}'")
        print(f"Intent: {example['intent']}")
        print(f"Entities: {example['entities']}")
        print("---")
    
    return wine_data

if __name__ == "__main__":
    # Run the integration
    # Replace with your actual JSONL file path
    jsonl_file = "wine_reviews.jsonl"  # Your wine data file
    
    try:
        wine_intelligence = integrate_with_aimee(jsonl_file)
        print(f"\n✅ Successfully processed wine data!")
        print(f"📊 Stats: {wine_intelligence['stats']}")
        
    except FileNotFoundError:
        print(f"❌ File not found: {jsonl_file}")
        print("Please update the file path to your wine JSONL file")
    except Exception as e:
        print(f"❌ Error processing wine data: {e}")