"""Edge-TTS helper: generates Brazilian Portuguese speech and real WordBoundary timings."""
import asyncio
import json
from pathlib import Path

import edge_tts

VOICE_CANDIDATES = ("pt-BR-FranciscaNeural", "pt-BR-AntonioNeural")


async def _generate(text: str, audio_path: str, json_path: str, voice: str):
    communicate = edge_tts.Communicate(text, voice)
    cues = []
    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            kind = chunk.get("type")
            if kind == "audio":
                audio_file.write(chunk["data"])
            elif kind == "WordBoundary":
                # Edge-TTS offsets/durations are 100-nanosecond ticks.
                offset = int(chunk.get("offset", 0))
                duration = int(chunk.get("duration", 0))
                word = str(chunk.get("text", "")).strip()
                if word:
                    start_ms = max(0, round(offset / 10_000))
                    end_ms = max(start_ms + 1, round((offset + duration) / 10_000))
                    cues.append({"text": word, "startMs": start_ms, "endMs": end_ms})
    if not cues:
        raise RuntimeError("Edge-TTS não retornou eventos WordBoundary; timestamps reais indisponíveis.")
    Path(json_path).write_text(json.dumps(cues, ensure_ascii=False, indent=2), encoding="utf-8")
    return cues


def generate_narration_with_timestamps(text: str, audio_path: str, json_path: str, voice: str = "pt-BR-FranciscaNeural"):
    """Synchronous wrapper for Flask handlers."""
    return asyncio.run(_generate(text, audio_path, json_path, voice))
