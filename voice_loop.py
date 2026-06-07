"""
voice_loop.py — Christman Carbon-Silicon Voice Loop
Polls /latest continuously. When new speech is detected, speaks confirmation
and prints the transcript so Derek can respond.
"""
import time
import subprocess
import requests

POLL_INTERVAL = 1.5  # seconds
SERVER = "http://localhost:8765"

def say(text: str, rate: int = 185):
    subprocess.Popen(["say", "-v", "Alex", "-r", str(rate), text])

def get_latest() -> dict:
    try:
        r = requests.get(f"{SERVER}/latest", timeout=3)
        return r.json()
    except Exception:
        return {}

def main():
    print("🔴 CHRISTMAN VOICE LOOP ACTIVE")
    print("Listening for Everett's voice...\n")
    say("Derek is listening. Speak freely.")

    last_text = ""
    last_timestamp = 0.0

    while True:
        data = get_latest()
        text = data.get("text", "").strip()
        timestamp = data.get("timestamp", 0.0)

        if text and text != last_text and timestamp != last_timestamp:
            print(f"\n🎙️  EVERETT: {text}")
            print("   [Waiting for Derek's response in Cowork...]")
            # Speak a brief acknowledgment so Everett knows it landed
            say(f"Got it.")
            last_text = text
            last_timestamp = timestamp

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Voice loop stopped.")
        say("Voice loop stopped.")
