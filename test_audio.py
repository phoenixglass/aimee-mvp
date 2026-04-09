import os
from elevenlabs import generate, set_api_key

api_key = os.getenv('ELEVENLABS_API_KEY')
print(f"API Key: {api_key[:10] if api_key else 'NOT FOUND'}...")

try:
    # Set the API key
    set_api_key(api_key)
    
    # Generate audio using the correct method
    audio = generate(
        text="This is a test of Aimee's voice",
        voice="Rachel",
        model="eleven_monolingual_v1"
    )
    
    # Save audio
    with open("test_audio.mp3", "wb") as f:
        f.write(audio)
    
    print("✅ Audio generated successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")