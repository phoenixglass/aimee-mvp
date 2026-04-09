
import speech_recognition as sr
import pandas as pd
from datetime import datetime
import os
from difflib import get_close_matches
import requests
import time
import tempfile
import pygame

# Load inventory CSV
df = pd.read_csv("inventory.csv")

# ElevenLabs config
ELEVENLABS_API_KEY = "sk_17254b66372cebc52de070e2d8584e0309333848556a0065"  # 🔐 PASTE YOUR API KEY HERE
VOICE_ID = "rzsnuMd2pwYz1rGtMIVI"  # Your custom Aimee voice ID

# Try to use Desktop path for log file
try:
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(desktop_path, exist_ok=True)
    log_path = os.path.join(desktop_path, "aimee_query_log.txt")
except Exception as e:
    print(f"⚠️ Couldn't use Desktop path: {e}")
    log_path = "aimee_query_log.txt"

def log_interaction(query, response):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_path, "a") as log_file:
            log_file.write(f"{timestamp} | QUERY: {query} | RESPONSE: {response}\n")
        print(f"💾 LOGGED to {log_path}")
    except Exception as e:
        print(f"❌ Logging failed: {e}")

def fuzzy_match_name(name, choices):
    match = get_close_matches(name.lower(), [n.lower() for n in choices], n=1, cutoff=0.6)
    if match:
        for choice in choices:
            if choice.lower() == match[0]:
                return choice
    return None

def find_info(query):
    query = query.lower()
    wine_names = df["wine_name"].tolist()
    customers = df["customer_last_ordered"].tolist()

    for _, row in df.iterrows():
        customer = row["customer_last_ordered"].lower()
        if customer in query:
            response = f"{row['customer_last_ordered']} last ordered {row['wine_name']}."
            log_interaction(query, response)
            return response

    for _, row in df.iterrows():
        wine_name = row["wine_name"]
        wine_keywords = wine_name.lower().split()
        if all(word in query for word in wine_keywords) or any(word in query for word in wine_keywords):
            matched_name = fuzzy_match_name(wine_name, wine_names)
            if matched_name:
                row = df[df["wine_name"] == matched_name].iloc[0]
                if "inventory" in query or "in stock" in query or "how much" in query:
                    response = f"We have {row['inventory']} bottles of {matched_name} in stock."
                elif "price" in query or "cost" in query:
                    response = f"The price of {matched_name} is {row['price']}."
                elif "ordered" in query or "last customer" in query or "who" in query:
                    response = f"The last customer to order {matched_name} was {row['customer_last_ordered']}."
                else:
                    response = f"{matched_name}: {row['inventory']} bottles at {row['price']} (last ordered by {row['customer_last_ordered']})"
                log_interaction(query, response)
                return response

    response = "Sorry, I couldn't find information about that wine or customer."
    log_interaction(query, response)
    return response

def speak_with_elevenlabs(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_audio.write(response.content)
            temp_audio_path = temp_audio.name
        pygame.mixer.init()
        pygame.mixer.music.load(temp_audio_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        os.remove(temp_audio_path)
    else:
        print(f"❌ ElevenLabs API error: {response.status_code}")
        print(response.text)

def transcribe_and_respond():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("🎤 Speak your wine question...")

    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source, timeout=5)

    try:
        text = recognizer.recognize_google(audio)
        print(f"📝 You said: {text}")
        response = find_info(text)
        print(f"🤖 Response: {response}")
        speak_with_elevenlabs(response)
    except sr.UnknownValueError:
        print("❌ Could not understand audio.")
    except sr.RequestError as e:
        print(f"❌ Speech recognition error: {e}")

if __name__ == "__main__":
    transcribe_and_respond()
