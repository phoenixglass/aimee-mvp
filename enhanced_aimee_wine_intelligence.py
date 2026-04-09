# enhanced_aimee_wine_intelligence.py
# Enhanced wine intelligence with JSONL data integration

import json
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict

class EnhancedAimeeWineIntelligence:
    def __init__(self, wine_data_file: str = "wine_intelligence_data.json"):
        self.wine_data = {}
        self.taste_profiles = {}
        self.recommendation_mappings = {}
        self.common_descriptors = {}
        
        # Load wine intelligence data
        try:
            with open(wine_data_file, 'r', encoding='utf-8') as f:
                self.wine_data = json.load(f)
                self.taste_profiles = self.wine_data.get('taste_profiles', {})
                self.recommendation_mappings = self.wine_data.get('recommendation_engine', {})
                self.common_descriptors = self.wine_data.get('common_descriptors', {})
            print(f"✅ Loaded wine intelligence data: {self.wine_data.get('stats', {})}")
        except FileNotFoundError:
            print(f"⚠️ Wine intelligence file not found: {wine_data_file}")
        except Exception as e:
            print(f"⚠️ Error loading wine intelligence: {e}")
    
    def handle_taste_query(self, taste_descriptors: List[str]) -> str:
        """Enhanced taste query handling with JSONL data"""
        if not taste_descriptors:
            return "I'd be happy to help you find the perfect wine. What flavors do you enjoy?"
        
        # Find wines matching the taste descriptors
        matching_wines = []
        for descriptor in taste_descriptors:
            descriptor_lower = descriptor.lower()
            
            # Check recommendation mappings
            if descriptor_lower in self.recommendation_mappings:
                wine_ids = self.recommendation_mappings[descriptor_lower][:3]  # Top 3
                for wine_id in wine_ids:
                    if str(wine_id) in self.taste_profiles:
                        wine_profile = self.taste_profiles[str(wine_id)]
                        matching_wines.append({
                            'id': wine_id,
                            'review': wine_profile.get('review', ''),
                            'descriptor': descriptor_lower
                        })
        
        if matching_wines:
            # Return recommendation based on actual wine data
            top_wine = matching_wines[0]
            review_snippet = top_wine['review'][:100] + "..." if len(top_wine['review']) > 100 else top_wine['review']
            
            return f"Perfect! For {', '.join(taste_descriptors)} wines, I recommend checking out wine #{top_wine['id']}. Reviews say: '{review_snippet}' I can pull more options if you'd like."
        else:
            # Fallback to general recommendations
            return f"Great taste! For {', '.join(taste_descriptors)} wines, I'd suggest exploring our {self._get_category_suggestions(taste_descriptors)} selection. Let me check our current inventory."
    
    def handle_pairing_query(self, food_type: str) -> str:
        """Enhanced food pairing with wine review insights"""
        
        pairing_map = {
            'seafood': ['crisp', 'light', 'mineral', 'citrus', 'dry'],
            'red meat': ['bold', 'full', 'tannic', 'oak', 'robust'],
            'cheese': ['smooth', 'medium', 'fruit', 'balanced'],
            'celebration': ['sparkling', 'elegant', 'crisp', 'festive'],
            'spicy': ['smooth', 'fruity', 'medium', 'cooling']
        }
        
        descriptors = pairing_map.get(food_type.lower(), ['balanced', 'versatile'])
        
        # Find wines with these characteristics
        recommended_wines = []
        for descriptor in descriptors:
            if descriptor in self.recommendation_mappings:
                wine_ids = self.recommendation_mappings[descriptor][:2]
                for wine_id in wine_ids:
                    if str(wine_id) in self.taste_profiles:
                        recommended_wines.append({
                            'id': wine_id,
                            'descriptor': descriptor,
                            'review': self.taste_profiles[str(wine_id)].get('review', '')
                        })
        
        if recommended_wines:
            top_pick = recommended_wines[0]
            return f"For {food_type}, I'd recommend wine #{top_pick['id']} - it's {top_pick['descriptor']} and pairs beautifully. Want me to check availability?"
        else:
            return f"For {food_type}, I'd suggest looking for {', '.join(descriptors)} wines. Let me check what we have in stock."
    
    def get_wine_recommendations_by_preference(self, customer_input: str, limit: int = 5) -> List[Dict]:
        """Get wine recommendations based on customer natural language input"""
        customer_lower = customer_input.lower()
        
        # Extract taste descriptors from customer input
        found_descriptors = []
        all_descriptors = set()
        for category_descriptors in self.common_descriptors.values():
            all_descriptors.update([desc.lower() for desc in category_descriptors])
        
        for descriptor in all_descriptors:
            if descriptor in customer_lower:
                found_descriptors.append(descriptor)
        
        # Get wine recommendations
        wine_matches = []
        for descriptor in found_descriptors:
            if descriptor in self.recommendation_mappings:
                wine_ids = self.recommendation_mappings[descriptor]
                for wine_id in wine_ids:
                    if str(wine_id) in self.taste_profiles:
                        wine_profile = self.taste_profiles[str(wine_id)]
                        wine_matches.append({
                            'vintage_id': wine_id,
                            'matched_descriptor': descriptor,
                            'review': wine_profile.get('review', ''),
                            'categories': {k: v for k, v in wine_profile.items() 
                                         if k not in ['vintage_id', 'review'] and v}
                        })
        
        # Remove duplicates and limit results
        seen_ids = set()
        unique_matches = []
        for wine in wine_matches:
            if wine['vintage_id'] not in seen_ids:
                seen_ids.add(wine['vintage_id'])
                unique_matches.append(wine)
            if len(unique_matches) >= limit:
                break
        
        return unique_matches
    
    def _get_category_suggestions(self, descriptors: List[str]) -> str:
        """Get wine category suggestions based on descriptors"""
        descriptor_categories = {
            'fruit': ['fruity', 'berry', 'cherry', 'apple', 'citrus'],
            'body': ['light', 'medium', 'full', 'bold'],
            'wood': ['oak', 'vanilla', 'spice'],
            'mineral': ['crisp', 'mineral', 'stone']
        }
        
        for category, keywords in descriptor_categories.items():
            for descriptor in descriptors:
                if descriptor.lower() in keywords:
                    return category
        
        return "premium"
    
    def get_stats(self) -> Dict:
        """Get wine intelligence statistics"""
        return self.wine_data.get('stats', {
            'total_wines': 0,
            'wines_with_profiles': 0,
            'unique_descriptors': 0
        })

# Integration function for your main Aimee system
def integrate_enhanced_wine_intelligence():
    """Replace the existing wine intelligence in your main system"""
    return EnhancedAimeeWineIntelligence()

# Updated handler functions for your main pipeline
def handle_enhanced_taste_query(taste_descriptors: List[str], wine_intelligence) -> str:
    """Enhanced taste query handler for main pipeline"""
    if hasattr(wine_intelligence, 'handle_taste_query'):
        return wine_intelligence.handle_taste_query(taste_descriptors)
    else:
        # Fallback if using old system
        return "I'd be happy to help you find wines with those characteristics."

def handle_enhanced_pairing_query(food_type: str, wine_intelligence) -> str:
    """Enhanced pairing query handler for main pipeline"""
    if hasattr(wine_intelligence, 'handle_pairing_query'):
        return wine_intelligence.handle_pairing_query(food_type)
    else:
        # Fallback if using old system
        return f"I can help you find wines that pair well with {food_type}."

def handle_wine_recommendation_request(customer_input: str, wine_intelligence) -> str:
    """New handler for general wine recommendation requests"""
    if hasattr(wine_intelligence, 'get_wine_recommendations_by_preference'):
        recommendations = wine_intelligence.get_wine_recommendations_by_preference(customer_input)
        
        if recommendations:
            top_rec = recommendations[0]
            review_snippet = top_rec['review'][:120] + "..." if len(top_rec['review']) > 120 else top_rec['review']
            
            response = f"Based on '{customer_input}', I found wine #{top_rec['vintage_id']} "
            response += f"(matches: {top_rec['matched_descriptor']}). "
            response += f"Review: '{review_snippet}' "
            response += f"Want details on {len(recommendations)} total matches?"
            
            return response
        else:
            return f"I heard '{customer_input}'. Let me check our inventory for wines matching those preferences."
    else:
        return f"I can help you find wines based on '{customer_input}'. Let me check what we have."

# Test the enhanced system
if __name__ == "__main__":
    # Test the enhanced wine intelligence
    enhanced_wine = EnhancedAimeeWineIntelligence()
    
    print("=== ENHANCED WINE INTELLIGENCE TEST ===")
    
    # Test taste queries
    test_queries = [
        "I like fruity wines",
        "Something bold and oaky", 
        "Light and crisp",
        "I want something with vanilla notes"
    ]
    
    for query in test_queries:
        descriptors = query.lower().split()
        response = enhanced_wine.handle_taste_query(descriptors)
        print(f"\nCustomer: '{query}'")
        print(f"Aimee: {response}")
    
    # Test recommendations
    print(f"\n=== RECOMMENDATION TEST ===")
    recs = enhanced_wine.get_wine_recommendations_by_preference("fruity and smooth wine")
    print(f"Found {len(recs)} recommendations for 'fruity and smooth wine'")
    
    if recs:
        print(f"Top pick: Wine #{recs[0]['vintage_id']} - {recs[0]['matched_descriptor']}")
    
    print(f"\n=== STATS ===")
    print(enhanced_wine.get_stats())