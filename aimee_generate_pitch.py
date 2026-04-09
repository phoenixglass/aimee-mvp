from elevenlabs import generate, save, Voice, VoiceSettings
from dotenv import load_dotenv
import os

load_dotenv()

# 🔥 PITCH TEMPLATES
pitch_templates = {
    "elegant": "Hi {name}, I’ve set aside a few bottles of {wine} — elegant, expressive, and exactly what you asked for. Would you like to try one?",
    "urgent": "{name}, quick heads-up — I’ve got {wine}, but it’s moving fast. Should I hold a case?",
    "casual": "Hey {name}, just got {wine} in. Thought of you. Want me to bring one by?",
    "romantic": "{name}, this {wine} is a mood. It’s whispering your name. Want to see why?",
    "analytical": "This {wine} offers incredible cost-per-pour performance. Let me run the numbers for you."
}

# Voice settings
voice_name = "Rachel"  # Use your actual voice clone name later
voice_settings = VoiceSettings(stability=0.35, similarity_boost=0.8, style=0.3, use_speaker_boost=True)

# Input
name = "Sofia"
wine = "Rock Angel rosé"
tone = "elegant"

# Generate text
text = pitch_templates[tone].format(name=name, wine=wine)

# Generate audio
audio = generate(
    text=text,
    voice=Voice(name=voice_name, settings=voice_settings),
    model="eleven_monolingual_v1"
)

# Save MP3
with open("aimee_pitch_output.mp3", "wb") as f:
    save(audio, f)

print("✅ Aimee pitch saved as 'aimee_pitch_output.mp3'")

