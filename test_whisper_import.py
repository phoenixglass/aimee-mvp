import whisper

model = whisper.load_model("base")
result = model.transcribe("clip_011.wav")
print(result["text"])
