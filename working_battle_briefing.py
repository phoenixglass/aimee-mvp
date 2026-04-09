from elevenlabs import set_api_key, generate, play
from dotenv import load_dotenv
import os

load_dotenv()

# Set your API key
set_api_key(os.getenv("ELEVENLABS_API_KEY"))

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
    
    # Use ElevenLabs 1.1.0 correct method
    audio = generate(
        text=clean_text,
        voice="Rachel",  # Use built-in voice first
        model="eleven_monolingual_v1"
    )
    
    # Save the audio
    with open("battle_briefing.mp3", "wb") as f:
        f.write(audio)
    
    print("✅ Battle briefing saved as battle_briefing.mp3")

if __name__ == "__main__":
    generate_battle_briefing()