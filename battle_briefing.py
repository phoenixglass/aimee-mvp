from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
import tempfile
import os

load_dotenv()

# Use EXACTLY the same setup as your main Aimee system
elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Sample accounts
daily_accounts = [
    {
        "priority": "🔥",
        "name": "LeBella's Fine Wine", 
        "intel": "Bordeaux order due. Sofia usually reorders every 21 days. It's day 23.",
        "value": "24000"
    },
    {
        "priority": "⚠️",
        "name": "DB Fine Wine",
        "intel": "Asked for rosé samples 2 days ago. Recommend Rock Angel.",
        "value": "9000"
    }
]

def clean_text_for_tts(text):
    import re
    # Remove emojis
    text = re.sub(r'[🔥⚠️🧊💰📍🍷]', '', text)
    # Replace money
    text = re.sub(r'\$(\d+)', r'\1 dollars', text)
    return text.strip()

def generate_battle_briefing():
    text = "Good morning Phoenix. Here's today's battlefield. LeBella's Fine Wine: Bordeaux order due, Sofia usually reorders every 21 days, it's day 23, 24000 dollars at stake."
    
    clean_text = clean_text_for_tts(text)
    
    # Use the SAME method as your working Aimee system
    audio = elevenlabs_client.text_to_speech.convert(
        voice_id="rzsnuMd2pwYz1rGtMIVI",  # Your Aimee voice
        text=clean_text,
        model_id="eleven_multilingual_v2"
    )
    
    # Convert to bytes
    if hasattr(audio, '__iter__'):
        audio_bytes = b"".join(audio)
    else:
        audio_bytes = audio
    
    # Save file
    with open("battle_briefing.mp3", "wb") as f:
        f.write(audio_bytes)
    
    print("✅ Battle briefing saved as battle_briefing.mp3")

if __name__ == "__main__":
    generate_battle_briefing()