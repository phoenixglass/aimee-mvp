#!/usr/bin/env python3
"""
Real Wine Dataset Extractor for Aimee
Converts the 45,000+ wine dataset into Aimee's intelligence format
"""

import pandas as pd
import json
import re
import numpy as np
from collections import defaultdict
import random

class RealWineExtractor:
    def __init__(self, csv_file="cleaned_wine_dataset_for_aimee.csv"):
        self.csv_file = csv_file
        self.wine_df = None
        self.taste_keywords = self.build_taste_keywords()
        
    def build_taste_keywords(self):
        """Define taste keywords for extracting flavor profiles from reviews"""
        return {
            "fruity": ["berry", "apple", "pear", "cherry", "plum", "citrus", "lemon", "lime", 
                      "orange", "grapefruit", "peach", "apricot", "strawberry", "raspberry", 
                      "blackberry", "blueberry", "tropical", "mango", "pineapple"],
            
            "earthy": ["mineral", "stone", "rock", "earth", "soil", "dust", "forest", 
                      "mushroom", "truffle", "wet leaves", "barnyard"],
            
            "spicy": ["pepper", "spice", "cinnamon", "clove", "nutmeg", "ginger", 
                     "paprika", "herbs", "thyme", "rosemary", "sage"],
            
            "woody": ["oak", "wood", "cedar", "pine", "vanilla", "smoke", "tobacco", 
                     "leather", "tar", "coffee", "chocolate", "cocoa"],
            
            "floral": ["rose", "violet", "jasmine", "lavender", "honeysuckle", 
                      "elderflower", "acacia", "blossom"],
            
            "body_descriptors": {
                "light": ["light", "delicate", "subtle", "thin", "easy"],
                "medium": ["medium", "balanced", "moderate"],
                "full": ["full", "rich", "bold", "intense", "heavy", "powerful", "robust"]
            },
            
            "acidity_descriptors": {
                "low": ["soft", "mellow", "smooth", "round"],
                "medium": ["balanced", "fresh"],
                "high": ["crisp", "bright", "sharp", "tart", "zesty", "vibrant"]
            },
            
            "tannin_descriptors": {
                "low": ["smooth", "soft", "silky", "mellow"],
                "medium": ["structured", "firm"],
                "high": ["tannic", "bold", "grippy", "astringent", "dry"]
            }
        }
    
    def load_data(self):
        """Load and clean the wine dataset"""
        print("Loading wine dataset...")
        
        self.wine_df = pd.read_csv(self.csv_file)
        
        # Clean data
        self.wine_df = self.wine_df.dropna(subset=['wine_name', 'grape'])
        self.wine_df['region'] = self.wine_df['region'].fillna('')
        self.wine_df['review'] = self.wine_df['review'].fillna('')
        
        # Clean wine names (remove redundant "from" text)
        self.wine_df['clean_wine_name'] = self.wine_df['wine_name'].str.replace(r' from.*', '', regex=True)
        
        print(f"Loaded {len(self.wine_df)} wines")
        return self.wine_df
    
    def extract_taste_profile_from_review(self, review):
        """Extract taste characteristics from wine review text"""
        if not review or pd.isna(review):
            return self.get_default_taste_profile()
        
        review_lower = str(review).lower()
        
        # Initialize profile
        profile = {
            "body": 0.5,      # 0-1 scale
            "acidity": 0.5,
            "tannins": 0.3,   # Lower default for whites
            "sweetness": 0.2,
            "alcohol": 0.6
        }
        
        # Extract body
        body_score = 0
        for level, keywords in self.taste_keywords["body_descriptors"].items():
            for keyword in keywords:
                if keyword in review_lower:
                    if level == "light":
                        body_score = 0.3
                    elif level == "medium":
                        body_score = 0.6
                    elif level == "full":
                        body_score = 0.9
                    break
            if body_score > 0:
                break
        
        if body_score > 0:
            profile["body"] = body_score
        
        # Extract acidity
        acidity_score = 0
        for level, keywords in self.taste_keywords["acidity_descriptors"].items():
            for keyword in keywords:
                if keyword in review_lower:
                    if level == "low":
                        acidity_score = 0.3
                    elif level == "medium":
                        acidity_score = 0.6
                    elif level == "high":
                        acidity_score = 0.9
                    break
            if acidity_score > 0:
                break
        
        if acidity_score > 0:
            profile["acidity"] = acidity_score
        
        # Extract tannins
        tannin_score = 0
        for level, keywords in self.taste_keywords["tannin_descriptors"].items():
            for keyword in keywords:
                if keyword in review_lower:
                    if level == "low":
                        tannin_score = 0.2
                    elif level == "medium":
                        tannin_score = 0.6
                    elif level == "high":
                        tannin_score = 0.9
                    break
            if tannin_score > 0:
                break
        
        if tannin_score > 0:
            profile["tannins"] = tannin_score
        
        # Extract sweetness indicators
        sweet_keywords = ["sweet", "sugar", "honey", "syrup", "dessert"]
        dry_keywords = ["dry", "bone dry", "crisp"]
        
        if any(keyword in review_lower for keyword in sweet_keywords):
            profile["sweetness"] = 0.7
        elif any(keyword in review_lower for keyword in dry_keywords):
            profile["sweetness"] = 0.1
        
        return profile
    
    def extract_flavor_notes_from_review(self, review):
        """Extract flavor descriptors from review text"""
        if not review or pd.isna(review):
            return []
        
        review_lower = str(review).lower()
        found_flavors = []
        
        # Check all flavor categories
        for category, flavors in self.taste_keywords.items():
            if category.endswith("_descriptors"):
                continue  # Skip descriptor categories
            
            for flavor in flavors:
                if flavor in review_lower:
                    found_flavors.append(flavor)
        
        # Return top 5 unique flavors
        return list(set(found_flavors))[:5]
    
    def get_default_taste_profile(self):
        """Get default taste profile based on grape variety"""
        return {
            "body": 0.5,
            "acidity": 0.6,
            "tannins": 0.4,
            "sweetness": 0.2,
            "alcohol": 0.6
        }
    
    def get_grape_defaults(self, grape):
        """Get default characteristics for grape varieties"""
        grape_profiles = {
            "Cabernet Sauvignon": {"body": 0.9, "tannins": 0.8, "acidity": 0.6},
            "Merlot": {"body": 0.8, "tannins": 0.6, "acidity": 0.5},
            "Pinot Noir": {"body": 0.5, "tannins": 0.4, "acidity": 0.8},
            "Chardonnay": {"body": 0.7, "tannins": 0.1, "acidity": 0.6},
            "Sauvignon Blanc": {"body": 0.4, "tannins": 0.0, "acidity": 0.9},
            "Sangiovese": {"body": 0.7, "tannins": 0.7, "acidity": 0.8},
            "Shiraz/Syrah": {"body": 0.8, "tannins": 0.7, "acidity": 0.6},
            "Tempranillo": {"body": 0.7, "tannins": 0.6, "acidity": 0.7}
        }
        
        return grape_profiles.get(grape, {"body": 0.5, "tannins": 0.4, "acidity": 0.6})
    
    def get_food_pairings(self, grape, body_score, acidity_score):
        """Generate food pairings based on wine characteristics"""
        
        # Base pairings by grape
        grape_pairings = {
            "Cabernet Sauvignon": ["red meat", "aged cheese", "grilled lamb", "dark chocolate"],
            "Merlot": ["red meat", "pasta", "soft cheese", "roasted vegetables"],
            "Pinot Noir": ["salmon", "duck", "mushrooms", "soft cheese"],
            "Chardonnay": ["seafood", "poultry", "cream sauces", "soft cheese"],
            "Sauvignon Blanc": ["seafood", "salads", "goat cheese", "light appetizers"],
            "Sangiovese": ["Italian cuisine", "tomato dishes", "grilled meats", "aged cheese"],
            "Shiraz/Syrah": ["barbecue", "spicy dishes", "aged cheese", "game"],
            "Tempranillo": ["Spanish cuisine", "grilled meats", "aged cheese", "tapas"]
        }
        
        base_pairings = grape_pairings.get(grape, ["various dishes"])
        
        # Add pairings based on body and acidity
        if body_score > 0.7:
            base_pairings.extend(["rich sauces", "hearty dishes"])
        if acidity_score > 0.7:
            base_pairings.extend(["seafood", "salads"])
        
        return list(set(base_pairings))[:4]  # Return top 4 unique pairings
    
    def select_quality_wines(self, min_rating=4.0, max_wines=500):
        """Select high-quality wines from the dataset"""
        
        # Filter for quality wines
        quality_wines = self.wine_df[
            (self.wine_df['rating'] >= min_rating) & 
            (self.wine_df['review'].str.len() > 20)  # Substantial reviews
        ].copy()
        
        # Sample diverse wines
        sampled_wines = []
        
        # Get top wines by grape variety
        for grape in quality_wines['grape'].value_counts().head(15).index:
            grape_wines = quality_wines[quality_wines['grape'] == grape].nlargest(20, 'rating')
            sampled_wines.append(grape_wines)
        
        # Combine and sample
        selected_wines = pd.concat(sampled_wines).drop_duplicates().head(max_wines)
        
        print(f"Selected {len(selected_wines)} quality wines for Aimee")
        return selected_wines
    
    def create_aimee_wine_database(self):
        """Create the complete Aimee wine database"""
        
        if self.wine_df is None:
            self.load_data()
        
        # Select quality wines
        selected_wines = self.select_quality_wines()
        
        wine_database = {}
        
        for idx, wine in selected_wines.iterrows():
            # Create wine key
            wine_key = self.normalize_name(wine['clean_wine_name'])
            
            # Extract taste profile
            taste_profile = self.extract_taste_profile_from_review(wine['review'])
            
            # Apply grape-specific defaults
            grape_defaults = self.get_grape_defaults(wine['grape'])
            for key, value in grape_defaults.items():
                if key in taste_profile:
                    taste_profile[key] = (taste_profile[key] + value) / 2  # Blend with review
            
            # Extract flavor notes
            flavor_notes = self.extract_flavor_notes_from_review(wine['review'])
            
            # Add grape-specific flavors if none found
            if not flavor_notes:
                flavor_notes = self.get_default_flavors(wine['grape'])
            
            # Generate food pairings
            food_pairings = self.get_food_pairings(
                wine['grape'], 
                taste_profile['body'], 
                taste_profile['acidity']
            )
            
            # Create wine entry
            wine_database[wine_key] = {
                "full_name": wine['clean_wine_name'],
                "variety": wine['grape'],
                "region": wine['region'].strip(),
                "country": wine['country'],
                "vintage": int(wine['year']) if pd.notna(wine['year']) else None,
                "price": float(wine['price']) if pd.notna(wine['price']) else None,
                "rating": float(wine['rating']) if pd.notna(wine['rating']) else None,
                "taste_profile": taste_profile,
                "flavor_notes": flavor_notes,
                "food_pairings": food_pairings,
                "complexity_score": min(wine['rating'] / 5.0, 1.0) if pd.notna(wine['rating']) else 0.7,
                "description": self.generate_description(wine, taste_profile, flavor_notes),
                "original_review": wine['review'][:200] if wine['review'] else ""  # First 200 chars
            }
        
        return wine_database
    
    def normalize_name(self, name):
        """Normalize wine name for database key"""
        return re.sub(r'[^a-zA-Z0-9]', '_', str(name).lower()).strip('_')
    
    def get_default_flavors(self, grape):
        """Get default flavors for grape varieties"""
        grape_flavors = {
            "Cabernet Sauvignon": ["blackberry", "cedar", "vanilla"],
            "Merlot": ["plum", "chocolate", "herbs"],
            "Pinot Noir": ["cherry", "earth", "spice"],
            "Chardonnay": ["apple", "vanilla", "butter"],
            "Sauvignon Blanc": ["citrus", "grass", "mineral"],
            "Sangiovese": ["cherry", "herbs", "earth"],
            "Shiraz/Syrah": ["blackberry", "pepper", "smoke"],
            "Tempranillo": ["cherry", "leather", "vanilla"]
        }
        
        return grape_flavors.get(grape, ["fruit", "earth"])
    
    def generate_description(self, wine, taste_profile, flavor_notes):
        """Generate natural language description"""
        
        # Body description
        if taste_profile['body'] > 0.7:
            body_desc = "full-bodied"
        elif taste_profile['body'] > 0.4:
            body_desc = "medium-bodied"
        else:
            body_desc = "light-bodied"
        
        # Acidity description
        if taste_profile['acidity'] > 0.7:
            acidity_desc = "crisp"
        elif taste_profile['acidity'] > 0.4:
            acidity_desc = "balanced"
        else:
            acidity_desc = "soft"
        
        # Flavor description
        if flavor_notes:
            flavor_text = ", ".join(flavor_notes[:3])
            flavor_desc = f"featuring notes of {flavor_text}"
        else:
            flavor_desc = f"showcasing classic {wine['grape']} character"
        
        return f"A {body_desc} {wine['grape']} with {acidity_desc} acidity, {flavor_desc}."
    
    def generate_training_examples(self, wine_database):
        """Generate training examples for Aimee's classifier"""
        
        examples = []
        wine_list = list(wine_database.items())
        
        # Sample wines for examples
        sample_wines = random.sample(wine_list, min(50, len(wine_list)))
        
        for wine_key, wine_data in sample_wines:
            variety = wine_data['variety']
            flavors = wine_data['flavor_notes']
            
            # Taste preference queries
            if flavors:
                examples.extend([
                    {
                        "text": f"I want something with {flavors[0]} notes",
                        "intent": "taste_preference_query",
                        "entities": {"flavor_preference": flavors[0]}
                    },
                    {
                        "text": f"Find me wines like {wine_data['full_name']}",
                        "intent": "taste_based_recommendation",
                        "entities": {"reference_wine": wine_data['full_name']}
                    }
                ])
            
            # Variety preferences
            examples.append({
                "text": f"I love {variety}, what do you recommend?",
                "intent": "product_recommendation",
                "entities": {"variety_preference": variety}
            })
            
            # Food pairings
            for pairing in wine_data['food_pairings'][:2]:  # Use first 2 pairings
                examples.append({
                    "text": f"What wine goes with {pairing}?",
                    "intent": "wine_pairing_request",
                    "entities": {"food_type": pairing}
                })
        
        return examples
    
    def save_aimee_data(self, output_file="aimee_real_wine_data.json"):
        """Create and save complete Aimee wine database"""
        
        print("Creating Aimee wine database...")
        
        # Create wine database
        wine_database = self.create_aimee_wine_database()
        
        # Generate training examples
        training_examples = self.generate_training_examples(wine_database)
        
        # Create taste vocabulary
        taste_vocabulary = {
            "flavor_descriptors": [],
            "taste_categories": self.taste_keywords
        }
        
        # Extract all flavor descriptors from database
        all_flavors = set()
        for wine_data in wine_database.values():
            all_flavors.update(wine_data['flavor_notes'])
        
        taste_vocabulary["flavor_descriptors"] = sorted(list(all_flavors))
        
        # Complete Aimee data
        aimee_data = {
            "wine_database": wine_database,
            "taste_vocabulary": taste_vocabulary,
            "training_examples": training_examples,
            "stats": {
                "total_wines": len(wine_database),
                "total_varieties": len(set(wine['variety'] for wine in wine_database.values())),
                "total_countries": len(set(wine['country'] for wine in wine_database.values() if wine['country'])),
                "training_examples": len(training_examples)
            }
        }
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(aimee_data, f, indent=2)
        
        print(f"✅ Saved {len(wine_database)} wines to {output_file}")
        print(f"✅ Generated {len(training_examples)} training examples")
        print(f"✅ Included {len(taste_vocabulary['flavor_descriptors'])} flavor descriptors")
        
        return aimee_data

def main():
    extractor = RealWineExtractor()
    aimee_data = extractor.save_aimee_data()
    
    # Print summary
    stats = aimee_data['stats']
    print(f"\n🍷 AIMEE WINE DATABASE READY! 🍷")
    print(f"📊 {stats['total_wines']} wines from {stats['total_varieties']} varieties")
    print(f"🌍 {stats['total_countries']} countries represented")
    print(f"🎯 {stats['training_examples']} training examples generated")
    print(f"\nReady to make Aimee a wine expert! 🚀")

if __name__ == "__main__":
    main()