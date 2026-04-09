#!/usr/bin/env python3
# debug_aimee.py - Quick debug script to test Aimee's components

def test_enhanced_wine_intelligence():
    """Test if enhanced wine intelligence is working"""
    print("=== TESTING ENHANCED WINE INTELLIGENCE ===")
    
    try:
        from enhanced_aimee_wine_intelligence import EnhancedAimeeWineIntelligence
        wine_intel = EnhancedAimeeWineIntelligence()
        
        print("✅ Enhanced wine intelligence loaded successfully")
        
        # Test stats
        stats = wine_intel.get_stats()
        print(f"📊 Wine data stats: {stats}")
        
        if stats.get('total_wines', 0) > 0:
            print("✅ Wine data is loaded and available")
        else:
            print("❌ Wine data appears to be empty")
            
        return wine_intel
        
    except Exception as e:
        print(f"❌ Enhanced wine intelligence failed: {e}")
        return None

def test_classifier():
    """Test if classifier is working"""
    print("\n=== TESTING CLASSIFIER ===")
    
    try:
        from aimee_classifier import AimeeClassifier
        classifier = AimeeClassifier(data_file="aimee_training_data_tagged.json", threshold=0.2)
        
        print("✅ Classifier loaded successfully")
        
        # Test classification of the specific command
        test_command = "Brief me on Barcelona wine bar"
        result = classifier.classify(test_command)
        
        print(f"🔍 Test command: '{test_command}'")
        print(f"📋 Classification result: {result}")
        
        # Check if it recognizes Fairfield County commands
        fairfield_commands = [
            "Brief me on Barcelona Wine Bar",
            "What should I focus on today",
            "Tell me about Bin 100 Restaurant"
        ]
        
        print("\n🏢 Testing Fairfield County commands:")
        for cmd in fairfield_commands:
            result = classifier.classify(cmd)
            print(f"   '{cmd}' → {result['intent']} (confidence: {result['match_score']:.2f})")
        
        return classifier
        
    except Exception as e:
        print(f"❌ Classifier failed: {e}")
        return None

def test_fairfield_integration():
    """Test if Fairfield County integration exists"""
    print("\n=== TESTING FAIRFIELD COUNTY INTEGRATION ===")
    
    try:
        # Try to import Fairfield integration
        from aimee_fairfield_integration import (
            handle_customer_briefing, 
            handle_daily_priorities,
            get_customer_intelligence
        )
        
        print("✅ Fairfield integration found")
        
        # Test Barcelona briefing
        barcelona_brief = handle_customer_briefing("Barcelona Wine Bar")
        print(f"🍷 Barcelona briefing: {barcelona_brief[:100]}...")
        
        return True
        
    except ImportError as e:
        print(f"❌ Fairfield integration not found: {e}")
        print("💡 This might be why Aimee isn't giving detailed restaurant info")
        return False
    except Exception as e:
        print(f"❌ Fairfield integration error: {e}")
        return False

def test_full_pipeline():
    """Test the full pipeline with the problematic command"""
    print("\n=== TESTING FULL PIPELINE ===")
    
    try:
        # Import the main processing functions
        from fixed_aimee_voice_pipeline_full_v2 import (
            preprocess_wine_terminology,
            extract_key_details,
            detect_special_responses
        )
        
        test_transcript = "Brief me on Barcelona wine bar"
        print(f"🎯 Testing: '{test_transcript}'")
        
        # Step 1: Preprocessing
        processed = preprocess_wine_terminology(test_transcript)
        print(f"1️⃣ Preprocessed: '{processed}'")
        
        # Step 2: Special responses
        special = detect_special_responses(test_transcript)
        print(f"2️⃣ Special response: {special}")
        
        # Step 3: Classification (need to load classifier)
        try:
            from aimee_classifier import AimeeClassifier
            classifier = AimeeClassifier(data_file="aimee_training_data_tagged.json", threshold=0.2)
            classification = classifier.classify(processed)
            print(f"3️⃣ Classification: {classification}")
            
            # Step 4: Key details extraction
            intent = classification.get('intent', 'unknown')
            details = extract_key_details(test_transcript, intent)
            print(f"4️⃣ Key details: '{details}'")
            
        except Exception as e:
            print(f"❌ Pipeline test failed at classification: {e}")
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")

def main():
    """Run all debug tests"""
    print("🔍 AIMEE DEBUG SESSION")
    print("=" * 50)
    
    # Test each component
    wine_intel = test_enhanced_wine_intelligence()
    classifier = test_classifier()
    fairfield_available = test_fairfield_integration()
    test_full_pipeline()
    
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSIS:")
    
    if not wine_intel:
        print("❌ Enhanced wine intelligence is not working")
        print("💡 Run: python run_wine_processor.py")
    
    if not classifier:
        print("❌ Classifier is not working")
        print("💡 Check if aimee_training_data_tagged.json exists")
    
    if not fairfield_available:
        print("❌ Fairfield County integration missing")
        print("💡 This is likely why Aimee gives generic responses")
        print("💡 Need to create aimee_fairfield_integration.py")
    
    print("\n🚀 NEXT STEPS:")
    if not fairfield_available:
        print("1. Create Fairfield County intelligence module")
        print("2. Add restaurant briefing data")
        print("3. Update training data with Fairfield commands")

if __name__ == "__main__":
    main()