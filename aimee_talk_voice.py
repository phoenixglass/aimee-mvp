
import os
import time
import openai
import requests
import sounddevice as sd
from scipy.io.wavfile import write
import pygame
from aimee_prompt_generator import AimeeWinePromptBuilder

# Configuration
DURATION = 5  # seconds to record
SAMPLERATE = 44100  # standard audio sample rate
AUDIO_FILENAME = "input.wav"

# Load your keys
openai.api_key = "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"
ELEVENLABS_API_KEY = "sk_e9b78f1419369795ae4c03cb4f4968bc2115fb2bd229bb6a"
ELEVENLABS_VOICE_ID = "rzsnuMd2pwYz1rGtMIVI"

# Prompt builder
builder = AimeeWinePromptBuilder("cleaned_wine_dataset_for_aimee.csv", n_examples=3)

def record_audio():
    print("🎙️ Recording... Speak now.")
    audio = sd.rec(int(DURATION * SAMPLERATE), samplerate=SAMPLERATE, channels=1)
    sd.wait()
    write(AUDIO_FILENAME, SAMPLERATE, audio)
    print("✅ Recording complete.")

def transcribe_audio():
    print("🧠 Transcribing with Whisper...")
    with open(AUDIO_FILENAME, "rb") as f:
        from openai import OpenAI

client = OpenAI()
transcript = client.audio.transcriptions.create(model="whisper-1", file=f)

    return transcript["text"]

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
    print("🔊 Speaking with ElevenLabs...")
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
        headers={"xi-api-key": ELEVENLABS_API_KEY},
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

def main():
    while True:
        user_input = input("📣 Press ENTER to speak (or type 'q' to quit): ")
        if user_input.lower() == 'q':
            break

        record_audio()
        transcript = transcribe_audio()
        print(f"🗣️ You said: {transcript}")

        prompt = builder.format_prompt_block(transcript)
        reply = generate_response(prompt)
        print(f"Aimee: {reply}")
        speak_text(reply)
        time.sleep(1)

if __name__ == "__main__":
    main()
