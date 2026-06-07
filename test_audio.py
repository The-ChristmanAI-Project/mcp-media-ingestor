from faster_whisper import WhisperModel
from pathlib import Path
import sys

def test_transcribe(audio_file: str):
    print(f"🔊 Inhaling audio for the agents: {audio_file}")
    
    model = WhisperModel(
        "small", 
        device="cpu", 
        compute_type="int8"
    )
    
    segments, info = model.transcribe(
        audio_file,
        beam_size=5,
        vad_filter=True,
        word_timestamps=True
    )
    
    print(f"Language: {info.language} (prob: {info.language_probability:.2f})")
    print(f"Duration: {info.duration:.1f}s\n")
    
    full_text = []
    for segment in segments:
        print(f"[{segment.start:.2f}s → {segment.end:.2f}s] {segment.text}")
        full_text.append(segment.text.strip())
    
    print("\n=== FULL TRANSCRIPT FOR AGENTS ===")
    print(" ".join(full_text))
    return " ".join(full_text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_audio.py <audio_or_video_file>")
        sys.exit(1)
    test_transcribe(sys.argv[1])
