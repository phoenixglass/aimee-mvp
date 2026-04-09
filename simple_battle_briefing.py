import elevenlabs
from dotenv import load_dotenv
import os

load_dotenv()

def generate_battle_briefing():
    # Set API key using the old method
    elevenlabs.api_key = os.getenv("ELEVENLABS_API_KEY")
    
    text = "Good morning Phoenix. Here's today's battlefield. LeBella's Fine Wine Bordeaux order due, 24000 dollars at stake."
    
    try:
        # Try method 1: text_to_speech function
        audio = elevenlabs.text_to_speech(text, voice="Rachel")
        
        with open("battle_briefing.mp3", "wb") as f:
            f.write(audio)
        
        print("✅ Battle briefing saved!")
        
    except AttributeError:
        print("❌ text_to_speech not available")
        
        try:
            # Try method 2: TTS class
            audio = elevenlabs.TTS(text, voice="Rachel")
            
            with open("battle_briefing.mp3", "wb") as f:
                f.write(audio)
            
            print("✅ Battle briefing saved with TTS class!")
            
        except Exception as e:
            print(f"❌ All methods failed: {e}")

if __name__ == "__main__":
    generate_battle_briefing()