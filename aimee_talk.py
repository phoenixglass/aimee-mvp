
import os
import time
import speech_recognition as sr
from aimee_prompt_generator import AimeeWinePromptBuilder
import openai
import requests
import pygame

def speak_text(text):
    import requests

    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/YOUR_VOICE_ID",
        headers={"xi-api-key": "YOUR_ELEVENLABS_API_KEY"},
        json={"text": text}
    )

    with open("aimee_response.mp3", "wb") as f:
        f.write(response.content)

    pygame.mixer.init()
    pygame.mixer.music.load("aimee_response.mp3")
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        continue

    pygame.mixer.quit()
    os.remove("aimee_response.mp3")

# Load your OpenAI and ElevenLabs credentials
openai.api_key = "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"
ELEVENLABS_API_KEY = "sk_e9b78f1419369795ae4c03cb4f4968bc2115fb2bd229bb6a"
ELEVENLABS_VOICE_ID = "rzsnuMd2pwYz1rGtMIVI"

# Initialize prompt builder
builder = AimeeWinePromptBuilder("cleaned_wine_dataset_for_aimee.csv", n_examples=3)

def transcribe_audio():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎙️ Speak now...")
        audio = recognizer.listen(source)
        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return "Sorry, I didn't catch that."
        except sr.RequestError:
            return "Speech recognition service is unavailable."

def generate_response(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are Aimee, a smart, elegant wine assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response['choices'][0]['message']['content']

def speak_text(text):
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
        headers={"xi-api-key": ELEVENLABS_API_KEY},
        json={"text": text, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    )
    with open("aimee_response.mp3", "wb") as f:
        f.write(response.content)
    playsound("aimee_response.mp3")
    os.remove("aimee_response.mp3")

def main():
    while True:
        user_input = transcribe_audio()
        print(f"🗣️ You said: {user_input}")

        prompt = builder.format_prompt_block(user_input)
        print("🧠 Generating response...")
        reply = generate_response(prompt)
        print(f"Aimee: {reply}")

        speak_text(reply)
        time.sleep(1)

if __name__ == "__main__":
    main()
