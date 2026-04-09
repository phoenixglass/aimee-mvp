#!/usr/bin/env python3
"""
Quick ElevenLabs API Test - Updated API
"""
import os
from elevenlabs.client import ElevenLabs

def test_elevenlabs_simple():
    """Test ElevenLabs with correct API"""
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("❌ No API key found")
        return False
    
    print(f"✅ API Key: {api_key[:10]}...")
    
    try:
        # Initialize client
        client = ElevenLabs(api_key=api_key)
        
        # Test text
        text = "Barcelona Wine Bar is a premier establishment in Fairfield County."
        
        print(f"🎤 Testing: '{text}'")
        
        # Generate audio using the correct API
        audio = client.generate(
            text=text,
            voice="Rachel",
            model="eleven_monolingual_v1"
        )
        
        # Save audio
        with open("test_elevenlabs.mp3", "wb") as f:
            for chunk in audio:
                f.write(chunk)
        
        # Check file
        size = os.path.getsize("test_elevenlabs.mp3")
        print(f"✅ Generated audio: {size} bytes")
        
        if size > 1000:
            print("✅ ElevenLabs working correctly!")
            return True
        else:
            print("❌ Audio file too small")
            return False
            
    except Exception as e:
        print(f"❌ ElevenLabs error: {e}")
        return False

if __name__ == "__main__":
    test_elevenlabs_simple()