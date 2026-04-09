import requests
import os
from dotenv import load_dotenv
import re

load_dotenv()

# Your actual tactical accounts
tactical_accounts = [
    {
        "priority": "🔥",
        "name": "LaBella's Fine Wine & Spirits",
        "intel": "Bordeaux allocation meeting overdue. Sofia tracks 21-day cycles. Day 23 now. Wine Warehouse circling.",
        "value": "24000",
        "action": "Call Sofia today"
    },
    {
        "priority": "⚡",
        "name": "Barcelona Wine Bar - Norwalk", 
        "intel": "Spanish natural wine program expanding. Chef Misha needs rare Rioja recommendations.",
        "value": "35000",
        "action": "Send Rioja samples"
    },
    {
        "priority": "🎯",
        "name": "Spiga Wine Bar",
        "intel": "Dan Camporeale expects exclusive Italian allocations. Ultra-wealthy New Canaan clientele ready.",
        "value": "18000", 
        "action": "Pitch private cellar curation"
    }
]

def clean_text_for_tts(text):
    """Clean text for better TTS delivery"""
    # Remove emojis
    emoji_pattern = r'[🔥⚡🎯💰📍🍷⚠️🧊]'
    text = re.sub(emoji_pattern, '', text)
    
    # Replace money symbols with words
    text = re.sub(r'\$(\d+)K', r'\1 thousand dollars', text)
    text = re.sub(r'\$(\d+)', r'\1 dollars', text)
    
    # Replace abbreviations
    text = text.replace('&', 'and')
    
    return text.strip()

def generate_tactical_briefing():
    # Build tactical briefing
    lines = ["Good morning Phoenix. Here's your tactical battlefield."]
    
    total_value = 0
    
    for account in tactical_accounts:
        line = f"{account['name']}. {account['intel']}. {account['value']} dollars at stake. {account['action']}."
        lines.append(line)
        total_value += int(account['value'])
    
    lines.append(f"Total pipeline value: {total_value} dollars.")
    lines.append("Strike with precision. Execute with speed. Dominate the field.")
    
    full_text = " ".join(lines)
    clean_text = clean_text_for_tts(full_text)
    
    # Generate audio via HTTP
    url = "https://api.elevenlabs.io/v1/text-to-speech/rzsnuMd2pwYz1rGtMIVI"
    
    headers = {
        "Accept": "audio/mpeg", 
        "Content-Type": "application/json",
        "xi-api-key": os.getenv("ELEVENLABS_API_KEY")
    }
    
    data = {
        "text": clean_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.8,
            "style": 0.25,
            "use_speaker_boost": True
        }
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        with open("tactical_briefing.mp3", "wb") as f:
            f.write(response.content)
        print("✅ Tactical briefing saved as tactical_briefing.mp3")
        print(f"📊 Total pipeline: ${total_value:,}")
        print("🎯 Ready for battle.")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    generate_tactical_briefing()