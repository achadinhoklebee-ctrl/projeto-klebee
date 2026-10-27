"""Super Robô Klebee — Motor Pro Otimizado para Cloud (V145 - FIX DEFINITIVO)"""
from __future__ import annotations
import os, shutil, subprocess, uuid, traceback
from pathlib import Path
from typing import Any
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-PRO-FULL-FIX-V145-2026-10-27"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1080, 1920, 30
VOICE = os.getenv("KLEBEE_TTS_VOICE", "pt-BR-AntonioNeural")
RATE = os.getenv("KLEBEE_TTS_RATE", "+15%")
FONT_PATHS = [
    os.getenv("KLEBEE_FONT", ""), 
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
]

app = FastAPI(title="Super Robô Klebee — Pro Engine", version=VERSION)

def binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Executável obrigatório ausente: {name}")
    return path

def run(args: list[str], timeout: int = 400) -> subprocess.CompletedProcess:
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"Comando falhou ({p.returncode}): {(p.stderr or p.stdout)[-2500:]}")
    return p

def font(size: int):
    for p in FONT_PATHS:
        if p and Path(p).is_file():
            try: return ImageFont.truetype(p, size=size)
            except OSError: pass
    return ImageFont.load_default()

def wrap(draw, text, f, max_width):
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=f)[2] <= max_width:
            current = candidate
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines[:3]

def make_headline(path: Path, text: str):
    image = Image.new("RGBA", (W, 550), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    size = 130
    while size >= 70:
        f = font(size)
        lines = wrap(draw, text.upper(), f, W - 60)
        if lines and all(draw.textbbox((0, 0), line, font=f)[2] <= W - 60 for line in lines):
            break
        size -= 2
    f = font(max(size, 70))
    lines = wrap(draw, text.upper(), f, W - 60) or [text.upper()[:30]]
    heights = [draw.textbbox((0, 0), line, font=f, stroke_width=12)[3] for line in lines]
    y = max(20, (550 - sum(heights) - 20 * (len(lines)-1)) // 2)
    for line, h in zip(lines, heights):
        box = draw.textbbox((0, 0), line, font=f, stroke_width=12)
        x = max(10, (W - (box[2] - box[0])) // 2)
        draw.text((x, y), line, font=f, fill="#FFE500", stroke_width=14, stroke_fill=(0, 0, 0, 255))
        y += h + 20
    image.save(path)

def ass_time(s: float) -> str:
    n = max(0, round(s * 100))
    h, n = divmod(n, 360000)
    m, n = divmod(n, 6000)
    sec, cs = divmod(n, 100)
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

def esc_ass(s: str) -> str:
    return s.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")

async def make_voice(text: str, path: Path) -> list[dict[str, Any]]:
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    audio_bytes = bytearray()
    words = []
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            start = float(chunk.get("offset", 0)) / 10_000_000
            dur = float(chunk.get("duration", 0)) / 10_000_000
            word = str(chunk.get("text", "")).strip()
            if word:
                words.append({"text": word, "start": start, "end": start + dur})
    if not audio_bytes:
        raise RuntimeError("Edge TTS não gerou áudio.")
    with path.open("wb") as f:
        f.write(audio_bytes)
    if not words:
        clean_words = text.split()
        if clean_words:
            audio_duration = max(3.0, len(audio_bytes) / 16000.0)
            step = audio_duration / len(clean_words)
            for i, w in enumerate(clean_words):
                start = i * step
                words.append({"text": w, "start": start, "end": start + step})
    if not words:
        raise RuntimeError("Falha ao processar palavras da narração.")
    return words

def make_ass(path: Path, words: list[dict[str, Any]], duration: float):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,84,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,8,3,5,80,80,480,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    groups, current = [], []
    for word in words:
        if current and (len(current) >= 3 or word["start"] - current[-1]["end"] > 0.35):
            groups.append(current)
            current = []
        current.append(word)
    if current:
        groups.append(current)
    events = []
    for group in groups:
        for active_i, active in enumerate(group):
            start = max(0, active["start"])
            end = min(duration, max(active["end"], start + 0.15))
            if end <= start:
                continue
            parts = []
            for i, word in enumerate(group):
                token = esc_ass(word["text"])
                if i == active_i:
                    parts.append(r"{\c&H00E5FF& \b1}" + token + r"{\c&HFFFFFF& \b0}")
                else:
                    parts.append(token)
            events.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{' '.join(parts)}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")

def download(url: str, folder: Path) -> Path:
    opts = {
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
        "outtmpl": str(folder / "source.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "retries": 2,
        "socket_timeout": 25
    }
    with YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
    candidates = [p for p in folder.glob("source.*") if p.is_file() and p.stat().st_size > 100_000]
    if not candidates:
        raise RuntimeError("Download sem arquivo de vídeo válido.")
    return max(candidates, key=lambda p: p.stat().st_size)

def probe_duration(path: Path) -> float:
    p = run([binary("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], 60)
    try:
        return float(p.stdout.strip())
    except ValueError as e:
        raise RuntimeError("ffprobe não leu a duração.") from e

def render(source: Path, audio: Path, ass: Path, headline: Path, output: Path, duration: float):
    ass_path = str(ass.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    headline_path = str(headline.resolve()).replace("\\", "/")
    cmd = [
        binary("ffmpeg"), "-y",
        "-i", str(source),
        "-i", str(audio),
        "-i", headline_path,
        "-filter_complex", (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}[bg]; "
            f"[bg][2:v]overlay=0:0[with_headline]; "
            f"[with_headline]ass='{ass_path}'[v]; "
            f"[0:a]volume=0.18[a_music]; "
            f"[1:a]volume=1.1[a_voice]; "
            f"[a_music][a_voice]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[a_final]"
        ),
        "-map", "[v]", "-map", "[a_final]",
        "-t", f"{duration:.3f}",
        "-threads", "4",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "21",
        "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(output)
    ]
    run(cmd, timeout=400)

@app.get("/", response_class=HTMLResponse)
def home():
    return f"""
    <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
    <title>Super Robô Klebee - Pro Engine {VERSION}</title>
    <style>
    body{{background:#0f172a;color:#f8fafc;font-family:Arial,sans-serif;text-align:center;padding:60px 15px}}
    .card{{background:#1e293b;padding:40px;border-radius:16px;display:inline-block;max-width:650px;box-shadow:0 10px 25px rgba(0,0,0,0.5)}}
    h1{{color:#38bdf8}}p{{color:#94a3b8}}.btn{{background:#22c55e;color:white;padding:18px 36px;text-decoration:none;border-radius:10px;font-weight:bold;display:inline-block;margin-top:20px}}
    </style></head><body><div class="card">
    <h1>🚀 Super Robô Klebee V145 PRO FIX</h1>
    <p>Headline Gigante + Legenda Hormozi + Música Mixada</p>
    <a class="btn" href="/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA">🟢 GERAR VÍDEO PROFISSIONAL V145</a>
    </div></body></html>
    """

@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION, "ffmpeg": shutil.which("ffmpeg") or "missing"}

@app.get("/render-web")
async def render_web(video_url: str = Query("https://www.tiktok.com/@carey_collections/video/7688751450901597461"), headline: str = Query("ACHADINHO INCRÍVEL!")):
    job = uuid.uuid4().hex
    folder = JOBS / job
    folder.mkdir(parents=True, exist_ok=False)
    try:
        print(f"[{job}] Iniciando download de: {video_url}")
        source = download(video_url, folder)
        print(f"[{job}] Download concluído. Gerando áudio TTS...")
        audio = folder / "narration.mp3"
        narration_text = "Olha esse achadinho incrível para sua casa! Prático, moderno e vai facilitar demais a sua rotina. Corre no link da bio e garanta o seu antes que esgote!"
        words = await make_voice(narration_text, audio)
        audio_duration = probe_duration(audio)
        duration = min(16.0, max(10.0, audio_duration + 0.15))
        print(f"[{job}] Áudio gerado. Duração: {duration}s. Criando legendas e headline...")
        ass = folder / "captions.ass"
        make_ass(ass, words, duration)
        headline_img = folder / "headline.png"
        make_headline(headline_img, headline)
        output = folder / "klebee_video.mp4"
        print(f"[{job}] Iniciando renderização FFmpeg V145...")
        render(source, audio, ass, headline_img, output, duration)
        print(f"[{job}] Renderização V145 concluída!")
        return FileResponse(output, media_type="video/mp4", filename="super_robo_klebee_v145.mp4")
    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"ERRO CRITICO NO JOB {job}:\n{err_msg}")
        raise HTTPException(status_code=500, detail=f"Erro na renderização: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
