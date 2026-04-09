from flask import Flask, render_template, jsonify, send_file, request
import requests
import os
from dotenv import load_dotenv
import re
import tempfile
import uuid

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')

# Load .env from explicit path
load_dotenv(env_path)

# Debug print
print(f"Loading .env from: {env_path}")
print(f".env exists: {os.path.exists(env_path)}")
print(f"API Key loaded: {bool(os.getenv('ELEVENLABS_API_KEY'))}")
print(f"API Key length: {len(os.getenv('ELEVENLABS_API_KEY') or '')}")

app = Flask(__name__)

# Your tactical accounts database
tactical_accounts = {
    "labellas": {
        "priority": "🔥",
        "name": "LaBellas Fine Wine and Spirits",
        "intel": "Bordeaux allocation meeting overdue Sofia tracks 21 day cycles Day 23 now Wine Warehouse circling",
        "value": "24000",
        "action": "Call Sofia today",
        "contact": "Sofia Martinez",
        "location": "Riverside CT"
    },
    "barcelona_norwalk": {
        "priority": "⚡",
        "name": "Barcelona Wine Bar Norwalk", 
        "intel": "Spanish natural wine program expanding Chef Misha needs rare Rioja recommendations",
        "value": "35000",
        "action": "Send Rioja samples",
        "contact": "Chef Misha Ryklin",
        "location": "Norwalk CT"
    },
    "spiga": {
        "priority": "🎯",
        "name": "Spiga Wine Bar",
        "intel": "Dan Camporeale expects exclusive Italian allocations Ultra wealthy New Canaan clientele ready",
        "value": "18000", 
        "action": "Pitch private cellar curation",
        "contact": "Dan Camporeale",
        "location": "New Canaan CT"
    },
    "bin_100": {
        "priority": "💎",
        "name": "Bin 100 Restaurant",
        "intel": "Modern Italian Mediterranean with polished edge Hosts multi course wine dinners Gaps in natural wines and grower Champagne",
        "value": "28000",
        "action": "Propose boutique wine dinner collaboration",
        "contact": "Wine Director",
        "location": "Milford CT"
    },
    "elm": {
        "priority": "🏆",
        "name": "ELM Restaurant",
        "intel": "Refined New American Chef Luke Venner Cool climate Old World focus Hosts boutique wine dinners",
        "value": "22000",
        "action": "Lead with terroir driven small lot finds",
        "contact": "Chef Luke Venner", 
        "location": "New Canaan CT"
    }
}

pitch_templates = {
    "urgent": "Quick heads-up {contact} - I've got {wine} moving fast. Should I hold cases for {account}?",
    "elegant": "Hi {contact}, I've set aside exceptional {wine} bottles - elegant, expressive, exactly what {account} customers expect.",
    "casual": "Hey {contact}, just got {wine} in. Thought of {account} immediately. Want me to bring samples by?",
    "tactical": "{contact}, this {wine} solves your {gap} gap perfectly. Cost-per-pour performance is exceptional for {account}.",
    "exclusive": "{contact}, I have access to {wine} that nobody else can get. Perfect for {account}'s premium program."
}

def clean_text_for_tts(text):
    # Remove emojis
    emoji_pattern = r'[🔥⚡🎯💰📍⚠️🧊💎🏆]'
    text = re.sub(emoji_pattern, '', text)
    
    # Fix possessives
    text = text.replace("LaBella's", "LaBellas")
    
    # Clean up money
    text = text.replace('$', '')
    text = text.replace('&', 'and')
    
    # Remove ALL periods to avoid "dot" issue
    text = text.replace('.', ' ')
    
    # Clean up extra spaces
    text = ' '.join(text.split())
    
    return text.strip()

def generate_audio(text):
    clean_text = clean_text_for_tts(text)
    
    url = "https://api.elevenlabs.io/v1/text-to-speech/rzsnuMd2pwYz1rGtMIVI"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json", 
        "xi-api-key": "sk_17254b66372cebc52de070e2d8584e0309333848556a0065"
    }

    data = {
        "text": clean_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.75,
            "style": 0.2,
            "use_speaker_boost": True
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        filename = f"tactical_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(tempfile.gettempdir(), filename)
        
        with open(filepath, "wb") as f:
            f.write(response.content)
        
        return filepath
    else:
        raise Exception(f"ElevenLabs error: {response.status_code}")

@app.route('/')
def dashboard():
    return render_template('tactical_dashboard.html', accounts=tactical_accounts)

@app.route('/briefing/daily')
def daily_briefing():
    # Build as one flowing narrative
    text = "Good morning Phoenix, here's your tactical battlefield "
    
    total_value = 0
    for i, (account_id, account) in enumerate(tactical_accounts.items()):
        total_value += int(account['value'])
        
        if i == 0:
            text += f"First up, {account['name']}, "
        elif i == len(tactical_accounts) - 1:
            text += f"Finally, {account['name']}, "
        else:
            text += f"Next, {account['name']}, "
            
        text += f"{account['intel']} {account['value']} dollars at stake, {account['action']} "
    
    text += f"Total pipeline value is {total_value} dollars "
    text += "Strike with precision, execute with speed, dominate the field"
    
    try:
        audio_path = generate_audio(text)
        return send_file(audio_path, as_attachment=True, download_name="daily_briefing.mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/briefing/account/<account_id>')
def account_briefing(account_id):
    if account_id not in tactical_accounts:
        return jsonify({"error": "Account not found"}), 404
    
    account = tactical_accounts[account_id]
    
    text = f"Tactical brief for {account['name']}. Location: {account['location']}. Contact: {account['contact']}. Intelligence: {account['intel']}. Value at stake: {account['value']} dollars. Recommended action: {account['action']}. Execute with precision."
    
    try:
        audio_path = generate_audio(text)
        return send_file(audio_path, as_attachment=True, download_name=f"{account_id}_briefing.mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/pitch/generate', methods=['POST'])
def generate_pitch():
    data = request.json
    account_id = data.get('account_id')
    tone = data.get('tone', 'tactical')
    wine = data.get('wine', 'premium selection')
    gap = data.get('gap', 'portfolio')
    
    if account_id not in tactical_accounts:
        return jsonify({"error": "Account not found"}), 404
    
    account = tactical_accounts[account_id]
    template = pitch_templates.get(tone, pitch_templates['tactical'])
    
    pitch_text = template.format(
        contact=account['contact'],
        account=account['name'], 
        wine=wine,
        gap=gap
    )
    
    try:
        audio_path = generate_audio(pitch_text)
        return send_file(audio_path, as_attachment=True, download_name=f"pitch_{account_id}_{tone}.mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/accounts')
def get_accounts():
    return jsonify(tactical_accounts)

if __name__ == '__main__':
    app.run(debug=True, port=5001)