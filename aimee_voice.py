import os
from elevenlabs import generate, save, set_api_key

set_api_key(os.getenv("sk_e9b78f1419369795ae4c03cb4f4968bc2115fb2bd229bb6a"))  # Load from .env or set manually

VOICE_ID = "54Cze5LrTSyLgbO6Fhlc"

def synthesize_with_elevenlabs(text, filename="aimee_output.mp3"):
    audio = generate(text=text, voice=VOICE_ID, model="eleven_monolingual_v1")
    save(audio, filename)
    return filename

