import elevenlabs
from dotenv import load_dotenv
import os

load_dotenv()

def generate_battle_briefing():
    # Set API key
    elevenlabs.api_key = os.getenv("ELEVENLABS_API_KEY")
    
    text = "Good morning Phoenix. Here's today's battlefield. LeBella's Fine Wine Bordeaux order due, 24000 dollars at stake."
    
    try:
        # Method 1: Try direct text_to_speech call
        audio = elevenlabs.text_to_speech(
            text,
            voice="rzsnuMd2pwYz1rGtMIVI",
            model="eleven_monolingual_v1"
        )
        
        # Use the save function that's available
        elevenlabs.save(audio, "battle_briefing.mp3")
        
        print("✅ Battle briefing saved as battle_briefing.mp3")
        
    except Exception as e:
        print(f"❌ Method 1 failed: {e}")
        
        try:
            # Method 2: Try using Voice object
            from elevenlabs import Voice, VoiceSettings
            
            audio = elevenlabs.text_to_speech(
                text,
                voice=Voice(
                    voice_id="rzsnuMd2pwYz1rGtMIVI",
                    settings=VoiceSettings(stability=0.4, similarity_boost=0.8)
                ),
                model="eleven_monolingual_v1"
            )
            
            elevenlabs.save(audio, "battle_briefing.mp3")
            print("✅ Battle briefing saved with Voice object!")
            
        except Exception as e2:
            print(f"❌ Method 2 also failed: {e2}")
            print("Let's try the HTTP method...")

if __name__ == "__main__":
    generate_battle_briefing()