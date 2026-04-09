#!/usr/bin/env python3
"""
Simple Wine Intelligence for Aimee
"""
import os
import json
from typing import Dict, List, Any  # For type hints

# In aimee_wine_intelligence.py
class AimeeWineIntelligence:
    def __init__(self):
        print("Wine intelligence initialized!")
        self.database = [...]  # Your wine data

class AimeeWineIntelligence:
    def __init__(self, db_path='wine_database.json', verbose=False):
        """Initialize wine intelligence with database
        
        Args:
            db_path (str): Path to JSON wine database
            verbose (bool): Whether to print debug info
        """
        self.verbose = verbose
        
        # Debug output
        if self.verbose:
            print(f"\n[Wine DB] Loading from: {os.path.abspath(db_path)}")
        
        try:
            # Load wine database
            with open(db_path, 'r', encoding='utf-8') as f:
                self.database = json.load(f)
            
            # Debug output
            if self.verbose:
                print(f"[Wine DB] Successfully loaded:")
                print(f" - Wines: {len(self.database.get('wines', []))}")
                print(f" - Pairings: {len(self.database.get('pairings', {}))}")
                print(f" - Taste Profiles: {len(self.database.get('taste_profiles', {}))}")
                
                # Show sample data
                if 'wines' in self.database and len(self.database['wines']) > 0:
                    print("\nSample Wines:")
                    for wine in self.database['wines'][:3]:  # First 3 wines
                        print(f" - {wine.get('name')} ({wine.get('type', 'N/A')})")
        
        except FileNotFoundError:
            print(f"\n[Wine DB ERROR] File not found: {db_path}")
            raise
        except json.JSONDecodeError as e:
            print(f"\n[Wine DB ERROR] Invalid JSON: {str(e)}")
            raise
        except Exception as e:
            print(f"\n[Wine DB ERROR] {str(e)}")
            raise
    
    def find_wines_by_taste(self, descriptors):
        """Find wines matching taste descriptors"""
        matches = []
        for wine_key, wine in self.wine_database.items():
            # Check if any descriptor matches flavor notes
            wine_flavors = ' '.join(wine.get('flavor_notes', [])).lower()
            if any(desc.lower() in wine_flavors for desc in descriptors):
                matches.append(wine)
        return matches[:3]
    
    def get_wine_pairing(self, food_type):
        """Get wine recommendations for food"""
        matches = []
        for wine_key, wine in self.wine_database.items():
            # Check if food type matches any pairing
            pairings = ' '.join(wine.get('food_pairings', [])).lower()
            if food_type.lower() in pairings:
                matches.append(wine)
        return matches[:3]

def handle_taste_query(descriptors, wine_intel):
    """Handle taste preference queries"""
    matches = wine_intel.find_wines_by_taste(descriptors)
    if matches:
        wine = matches[0]
        return f"I'd recommend the {wine['full_name']}. {wine['description']}"
    return "I couldn't find wines matching those taste preferences."

def handle_pairing_query(food_type, wine_intel):
    """Handle food pairing requests"""
    matches = wine_intel.get_wine_pairing(food_type)
    if matches:
        wine = matches[0]
        return f"For {food_type}, I'd suggest the {wine['full_name']}. {wine['description']}"
    return f"I don't have specific pairing suggestions for {food_type}."