import os
import time
from gtts import gTTS

# 1. Setup
os.makedirs('uploads', exist_ok=True)
test_text = "This is a working audio test"
filename = os.path.join('uploads', f'test_{int(time.time())}.mp3')

# 2. Generate audio
print("Attempting to create audio file...")
try:
    tts = gTTS(text=test_text, lang='en')
    tts.save(filename)
    print(f"Success! File created at: {filename}")
    print(f"Absolute path: {os.path.abspath(filename)}")
except Exception as e:
    print(f"FAILED: {str(e)}")

# 3. Verify
print("\nDirectory contents:")
print(os.listdir('uploads'))