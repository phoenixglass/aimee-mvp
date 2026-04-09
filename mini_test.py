from elevenlabs import generate, save, Voice, VoiceSettings

audio = generate(
    text="This is a clean install test.",
    voice=Voice(name="Rachel", settings=VoiceSettings()),
    model="eleven_monolingual_v1"
)

with open("clean_test.mp3", "wb") as f:
    save(audio, f)

print("✅ Success. File saved.")

