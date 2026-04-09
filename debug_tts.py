import elevenlabs
from dotenv import load_dotenv
import os

load_dotenv()
elevenlabs.api_key = os.getenv("ELEVENLABS_API_KEY")

print("What's in elevenlabs.text_to_speech:")
print(dir(elevenlabs.text_to_speech))