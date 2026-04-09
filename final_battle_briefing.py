import elevenlabs
from dotenv import load_dotenv
import os

load_dotenv()

def generate_battle_briefing():
    # Set API key
    elevenlabs.api_key = os.getenv("ELEVENLABS_API_KEY")
    
    text = "Good morning Phoenix. Here's today's battlefield. LeBella's Fine Wine Bordeaux order due, 24000 dollars at stake."
    
    try:
        # Use YOUR Aimee voice ID (same as in your main system)
        audio = elevenlabs.text_to_speech.convert(
            text=text,
            voice_id="rzsnuMd2pwYz1rGtMIVI",  # Your Aimee voice
            model_id="eleven_monolingual_v1"
        )
        
        # Convert generator to bytes if needed
        if hasattr(audio, '__iter__') and not isinstance(audio, bytes):
            audio_bytes = b"".join(audio)
        else:
            audio_bytes = audio
        
        with open("battle_briefing.mp3", "wb") as f:
            f.write(audio_bytes)
        
        print("✅ Battle briefing saved as battle_briefing.mp3")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    generate_battle_briefing()