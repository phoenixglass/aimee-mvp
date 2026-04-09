import requests
import os
from dotenv import load_dotenv

load_dotenv()

def generate_battle_briefing():
    url = "https://api.elevenlabs.io/v1/text-to-speech/rzsnuMd2pwYz1rGtMIVI"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": os.getenv("ELEVENLABS_API_KEY")
    }
    
    data = {
        "text": "Good morning Phoenix. Here's today's battlefield. LeBella's Fine Wine Bordeaux order due, 24000 dollars at stake.",
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.8
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        with open("battle_briefing.mp3", "wb") as f:
            f.write(response.content)
        print("✅ Battle briefing saved via HTTP!")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    generate_battle_briefing()