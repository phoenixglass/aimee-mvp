#!/usr/bin/env python3
# run_wine_processor.py
# Quick runner to process your all_dataset.JSONL file

from wine_data_processor import integrate_with_aimee
import os

def main():
    jsonl_file = "all_dataset.JSONL"
    
    # Check if file exists
    if not os.path.exists(jsonl_file):
        print(f"❌ File not found: {jsonl_file}")
        print("Please make sure all_dataset.JSONL is in the same directory as this script")
        return
    
    print(f"🍷 Processing wine data from: {jsonl_file}")
    print("This may take a few minutes for large datasets...")
    
    try:
        # Process the wine data
        wine_intelligence = integrate_with_aimee(jsonl_file)
        
        print(f"\n🎉 SUCCESS! Wine intelligence enhanced!")
        print(f"📊 Processed: {wine_intelligence['stats']['total_wines']} wine reviews")
        print(f"🏷️  Generated: {len(wine_intelligence['training_examples'])} training examples")
        print(f"🍇 Unique descriptors: {wine_intelligence['stats']['unique_descriptors']}")
        
        print(f"\n📁 Output files created:")
        print(f"   - wine_intelligence_data.json (for Aimee integration)")
        
        print(f"\n✅ Ready to integrate with Aimee!")
        print(f"Next step: Update your main pipeline to use the enhanced wine intelligence")
        
    except Exception as e:
        print(f"❌ Error processing wine data: {e}")
        print(f"Please check that all_dataset.JSONL is a valid JSONL file")

if __name__ == "__main__":
    main()