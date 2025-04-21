import asyncio
import time
import os
from main import transcribe_file  # Your actual transcriber logic

# Path to the sample audio
SAMPLE_PATH = "blerbs/player_bench_sample.wav"
ITERATIONS = 5


def benchmark_transcriber():
    per_blerb_times = []
    
    print("\n--- Benchmark Start ---")
    total_start = time.perf_counter()

    for i in range(ITERATIONS):
        print(f"\n🔄 Run {i + 1}/{ITERATIONS}: {SAMPLE_PATH}")

        # Time only the transcription logic
        start = time.perf_counter()
        text = transcribe_file(SAMPLE_PATH, player_id="benchmark", timestamp=round(time.time() * 1000))
        elapsed = time.perf_counter() - start

        print(f"✅ Transcribed in {elapsed:.4f} seconds")
        per_blerb_times.append(elapsed)

    total_elapsed = time.perf_counter() - total_start

    avg_time = sum(per_blerb_times) / ITERATIONS
    print("\n--- Benchmark Results ---")
    print(f"Processed: {ITERATIONS} blerbs")
    print(f"Total transcription time: {total_elapsed:.2f} seconds")
    print(f"Avg time per blerb: {avg_time:.4f} seconds")


if __name__ == "__main__":
    benchmark_transcriber()
