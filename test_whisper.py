from faster_whisper import WhisperModel
import sys

model = WhisperModel(
    "small",           # or "base", "medium" depending on your hardware
    device="cpu",
    compute_type="int8"  # efficient for your Intel setup
)

audio_path = sys.argv[1] if len(sys.argv) > 1 else "test_audio.wav"

segments, info = model.transcribe(
    audio_path,
    beam_size=5,
    vad_filter=True,      # removes silence
    word_timestamps=True  # useful for precise parsing
)

print(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")
print(f"Transcription duration: {info.duration:.2f}s\n")

for segment in segments:
    print(f"[{segment.start:.2f}s → {segment.end:.2f}s] {segment.text}")
    for word in segment.words or []:
        print(f"  • {word.word} ({word.start:.2f}s)")
