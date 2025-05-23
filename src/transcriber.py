# main.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
import redis

import json
import os
import time
import uuid
import asyncio

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True  # Makes it easier to work with strings
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# model = WhisperModel("base", device="cuda", compute_type="float16")
model = WhisperModel("medium.en", device="cuda", compute_type="float16")
TRANSCRIPTS = []
blerb_queue = asyncio.Queue()

AUDIO_DIR = "blerbs"
os.makedirs(AUDIO_DIR, exist_ok=True)

async def blerb_worker():
    while True:
        file_path, player_id, timestamp = await blerb_queue.get()
        print(f"\n🔄 Processing blerb: {file_path}")
        start_time = time.perf_counter()

        text = "[ERROR]"
        try:
            if os.path.getsize(file_path) < 5000:
                raise Exception("Skipped: blob too small")


            segments, _ = model.transcribe(
                file_path,
                beam_size=10,
                language="en",
                task="transcribe",
                vad_filter=True,
                condition_on_previous_text=True  # For better long-form accuracy
            )
            text = " ".join([seg.text for seg in segments]).strip()
        except Exception as e:
            print(f"❌ Error transcribing {file_path}: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

        elapsed = time.perf_counter() - start_time
        entry = {
            "player_id": player_id,
            "timestamp": timestamp,
            "text": text,
            "elapsed": round(elapsed, 2)
        }

        # TRANSCRIPTS.append(entry)  # (comment this out)

        if(entry["text"].strip()):
            redis_client.rpush("transcripts:uncleaned", json.dumps({
                "player_id": entry["player_id"],
                "start_timestamp": entry["timestamp"],
                "text": entry["text"]
            }))
        else:
            print(f"🕳️ Skipped empty blerb from {entry['player_id']} at {entry['timestamp']}")

        print(f"✅ Done in {entry['elapsed']}s: {player_id}: {text}")
        print_transcript_log()

        blerb_queue.task_done()

def print_transcript_log():
    print("\n📝 Transcript so far:")

    transcript_list = redis_client.lrange("transcripts:uncleaned", 0, -1)

    for i, raw in enumerate(transcript_list, start=1):
        entry = json.loads(raw)
        print(f"{i:02d}. [{entry['player_id']}] ({entry['start_timestamp']}): {entry['text']}")
    
    print()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(blerb_worker())

@app.post("/upload-audio/")
async def upload_audio(
    file: UploadFile = File(...),
    player_id: str = Form(...),
    timestamp: int = Form(...)
):
    extension = os.path.splitext(file.filename)[-1]
    unique_id = uuid.uuid4().hex
    filename = f"{player_id}_{timestamp}_{unique_id}{extension}"
    print(f"📥 Received file: {filename}")
    file_path = os.path.join(AUDIO_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    await blerb_queue.put((file_path, player_id, timestamp))

    

    return JSONResponse({
        "status": "queued",
        "filename": filename
    })