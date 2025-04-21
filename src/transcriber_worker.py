# transcriber_worker.py
from faster_whisper import WhisperModel
import redis
import os
import json
import time

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
model = WhisperModel("medium.en", device="cuda", compute_type="float16")

print("🧠 Transcriber worker ready.")

while True:
    item = redis_client.lpop("transcription:queue")
    if not item:
        time.sleep(0.5)
        continue

    payload = json.loads(item)
    file_path = payload["file_path"]
    player_id = payload["player_id"]
    timestamp = payload["timestamp"]

    print(f"\n🔄 Transcribing {file_path}")
    start_time = time.perf_counter()
    try:
        if os.path.getsize(file_path) < 5000:
            raise Exception("Skipped: blob too small")

        segments, _ = model.transcribe(
            file_path,
            beam_size=10,
            language="en",
            task="transcribe",
            vad_filter=True,
            condition_on_previous_text=True
        )

        text = " ".join([seg.text for seg in segments]).strip()

    except Exception as e:
        text = "[ERROR]"
        print(f"❌ Error: {e}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    elapsed = round(time.perf_counter() - start_time, 2)
    print(f"✅ Done in {elapsed}s: {player_id}: {text}")

    if text and text != "[ERROR]":
        redis_client.rpush("transcripts:uncleaned", json.dumps({
            "player_id": player_id,
            "start_timestamp": timestamp,
            "text": text
        }))
