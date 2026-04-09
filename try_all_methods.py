import elevenlabs
from dotenv import load_dotenv
import os

load_dotenv()
elevenlabs.api_key = os.getenv("ELEVENLABS_API_KEY")

text = "Test audio generation"
voice_id = "rzsnuMd2pwYz1rGtMIVI"

methods_to_try = [
    lambda: elevenlabs.text_to_speech.generate(text=text, voice=voice_id),
    lambda: elevenlabs.text_to_speech(text, voice=voice_id),
    lambda: elevenlabs.generate(text=text, voice=voice_id),
    lambda: elevenlabs.text_to_speech.create(text=text, voice_id=voice_id),
]

for i, method in enumerate(methods_to_try):
    try:
        print(f"Method {i+1}: Trying...")
        audio = method()
        print(f"✅ Method {i+1} worked!")
        
        with open(f"test_method_{i+1}.mp3", "wb") as f:
            if hasattr(audio, '__iter__') and not isinstance(audio, bytes):
                f.write(b"".join(audio))
            else:
                f.write(audio)
        break
        
    except Exception as e:
        print(f"❌ Method {i+1} failed: {e}")

print("Done testing methods.")