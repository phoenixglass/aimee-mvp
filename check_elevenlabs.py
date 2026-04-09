import elevenlabs
from dotenv import load_dotenv
import os

load_dotenv()
elevenlabs.api_key = os.getenv("ELEVENLABS_API_KEY")

print("What's available in main elevenlabs module:")
available = [item for item in dir(elevenlabs) if not item.startswith('_')]
print(available)

# Check for common function names
common_functions = ['generate', 'tts', 'synthesize', 'speak', 'create_audio', 'voice_synthesis']
for func_name in common_functions:
    if hasattr(elevenlabs, func_name):
        print(f"✅ Found: {func_name}")
        try:
            func = getattr(elevenlabs, func_name)
            print(f"   Type: {type(func)}")
        except:
            pass