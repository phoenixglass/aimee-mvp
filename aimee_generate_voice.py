from elevenlabs import text_to_speech, VoiceSettings
from dotenv import load_dotenv
import os
from pydub import AudioSegment

load_dotenv()  # Loads ELEVEN_API_KEY from .env

# Your battle segments
text_segments = [
    "Good morning, Phoenix.",
    "Here’s today’s battlefield.",
    "Target One: LeBella’s Fine Wine. Bordeaux order is overdue. Sofia usually reorders every 21 days. It’s day 23. Wine Warehouse is circling.",
    "Estimated value: twenty-four thousand dollars.",
    "Target Two: DB Fine Wine. Sofia requested rosé samples two days ago. Suggested follow-up: Rock Angel or Domaine Tempier.",
    "Estimated value: nine thousand dollars.",
    "Target Three: 99 Bottles, Westport. No contact in three weeks. Last interest: local Pinot Noirs. Recommend Scar of the Sea or Belle Pente.",
    "Estimated value: fifteen thousand dollars.",
    "Would you like detailed intel, a draft pitch, or to skip?"
]

voice_name = "Rachel"  # swap with your Aimee voice name when ready
model = "eleven_multilingual_v2"
voice_settings = VoiceSettings(stability=0.35, similarity_boost=0.8, style=0.3, use_speaker_boost=True)

# Generate audio segments
segments = []
for i, line in enumerate(text_segments):
    audio = text_to_speech(
        text=line,
        voice=voice_name,
        model=model,
        voice_settings=voice_settings
    )
    filename = f"segment_{i:02}.mp3"
    with open(filename, "wb") as f:
        f.write(audio)
    segments.append(AudioSegment.from_file(filename))

# Stitch with 500ms pauses
pause = AudioSegment.silent(duration=500)
final_audio = AudioSegment.empty()
for segment in segments:
    final_audio += segment + pause

# Export final output
final_audio.export("aimee_briefing_final.mp3", format="mp3")
print("✅ Aimee's stitched battle briefing saved as: aimee_briefing_final.mp3")
