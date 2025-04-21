# blerb_receiver.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import redis
import uuid
import os
import time
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
AUDIO_DIR = "blerbs"
os.makedirs(AUDIO_DIR, exist_ok=True)

@app.post("/upload-audio/")
async def upload_audio(
    file: UploadFile = File(...),
    player_id: str = Form(...),
    timestamp: int = Form(...)
):
    extension = os.path.splitext(file.filename)[-1]
    unique_id = uuid.uuid4().hex
    filename = f"{player_id}_{timestamp}_{unique_id}{extension}"
    file_path = os.path.join(AUDIO_DIR, filename)

    print(f"📥 Received file: {filename}")
    with open(file_path, "wb") as f:
        f.write(await file.read())

    redis_client.rpush("transcription:queue", json.dumps({
        "file_path": file_path,
        "player_id": player_id,
        "timestamp": timestamp
    }))

    return JSONResponse({"status": "queued", "filename": filename})
