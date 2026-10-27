"""Super Robô Klebee — V150 - DEFINITIVO - SEM FUNDO PRETO + SINCRONIA PREMIERE"""
from __future__ import annotations
import os
import shutil
import subprocess
import uuid
import traceback
from pathlib import Path
from typing import Any
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-V150-DEFINITIVO"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1080, 1920, 30
VOICE = os.getenv("KLEBEE_TTS_VOICE", "pt-BR-AntonioNeural")
RATE = os.getenv("KLEBEE_TTS_RATE", "+15%")
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
]

app = FastAPI(title="Super Robô Klebee — Pro Engine", version=VERSION)

def binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Executavel obrigatorio ausente: {name}")
    return path

def run(args: list[str], timeout: int = 400) -> subprocess.CompletedProcess:
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"Comando falhou ({p.returncode}): {(p.stderr or p.stdout)[-2500:]}")
    return p

def font(size: int):
    for pth in FONT_PATHS:
        if Path(pth).is_file():
            try:
                return ImageFont.truetype(pth, size=size)
            except OSError:
                pass
    return ImageFont.load_default()

def wrap(draw, text, f, max_width):
    lines, cur = [], ""
    for w in text.split():
        cand = f"{cur} {w}".strip()
        if draw.textbbox((0, 0), cand, font=f, stroke_width=12)[2] <= max_width:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:3]

def make_headline(path: Path, text: str):
    image = Image.new("RGBA", (W, 520), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    size = 112
    while size >= 62:
        f = font(size)
        if wrap(draw, text.upper(), f, W - 100):
            break
        size -= 2
    f = font(max(size, 62))
    lines = wrap(draw, text.upper(), f, W - 100) or [text.upper()]
    y = 20
    for line in lines:
        box = draw.textbbox((0, 0), line, font=f, stroke_width=13)
        x = (W - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=f, fill="#FFE500", stroke_width=13, stroke_fill=(0, 0, 0, 255))
        y += box[3] - box[1] + 18
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
            st = float(chunk.get("offset", 0)) / 10_000_000
            dur = float(chunk.get("duration", 0)) / 10_000_000
            w = str(chunk.get("text", "")).strip()
            if w:
                words.append({"text": w, "start": st, "end": st + dur})
    if not audio_bytes:
        raise RuntimeError("Edge TTS nao gerou audio.")
    with path.open("wb") as f:
        f.write(audio_bytes)
    if not words:
        clean = text.split()
        dur = max(3.0, len(audio_bytes) / 16000.0)
        step = dur / max(1, len(clean))
        words = [{"text": w, "start": i * step, "end": (i + 1) * step} for i, w in enumerate(clean)]
    return words

def make_ass(path: Path, words: list[dict[str, Any]], duration: float):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,84,&H0000E5FF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,9,3,5,60,60,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    groups = []
    cur = []
    for w in words:
        cur.append(w)
        is_long = (w["end"] - cur[0]["start"]) > 1.2
        is_many = len(cur) >= 4
        is_pause = len(cur) > 1 and (w["start"] - cur[-2]["end"]) > 0.3
        if is_long or is_many or is_pause:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)

    events = []
    for g in groups:
        gs = g[0]["start"]
        ge = min(duration, g[-1]["end"] + 0.25)
        txt = ""
        for w in g:
            k = int(max(0.12, w["end"] - w["start"]) * 100)
            txt += f"{{\\k{k}}}{esc_ass(w['text'])} "
        events.append(f"Dialogue: 0,{ass_time(gs)},{ass_time(ge)},Caption,,0,0,0,,{txt.strip()}")

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
    cands = [p for p in folder.glob("source.*") if p.is_file() and p.stat().st_size > 100_000]
    if not cands:
        raise RuntimeError("Download sem arquivo valido.")
    return max(cands, key=lambda p: p.stat().st_size)

def probe_duration(path: Path) -> float:
    p = run([binary("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], 60)
    return float(p.stdout.strip())

def render(source: Path, audio: Path, ass: Path, headline: Path, output: Path, duration: float):
    ass_path = str(ass.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    hl_path = str(headline.resolve()).replace("\\", "/")
    cmd = [
        binary("ffmpeg"), "-y",
        "-i", str(source),
        "-i", str(audio),
        "-i", hl_path,
        "-filter_complex", (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}[bg]; "
            f"[bg][2:v]overlay=0:45[with_headline]; "
            f"[with_headline]ass='{ass_path}'[v]; "
            f"[0:a]volume=0.22[a_music]; "
            f"[1:a]volume=1.15[a_voice]; "
            f"[a_music][a_voice]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[a_final]"
        ),
        "-map", "[v]",
        "-map", "[a_final]",
        "-t", f"{duration:.3f}",
        "-threads", "4",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output)
    ]
    run(cmd, timeout=400)

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="UTF-8"><title>Super Robo Klebee V150</title>
    <style>body{background:#0f172a;color:#f8fafc;font-family:Arial;text-align:center;padding:60px 15px}.card{background:#1e293b;padding:40px;border-radius:16px;display:inline-block;max-width:650px}.btn{background:#22c55e;color:white;padding:18px 36px;text-decoration:none;border-radius:10px;font-weight:bold;display:inline-block;margin-top:20px}</style>
    </head>
    <body><div class="card">
    <h1>ROBO KLEBEE V150 - DEFINITIVO</h1>
    <p>Headline transparente + Legenda Premiere Pro sincronizada</p>
    <a class="btn" href="/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA">GERAR VIDEO V150</a>
    </div></body></html>
    """

@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION, "ffmpeg": shutil.which("ffmpeg") or "missing"}

@app.get("/render-web")
async def render_web(video_url: str = Query("https://www.tiktok.com/@carey_collections/video/7688751450901597461"), headline: str = Query("ACHADINHO INCRIVEL!")):
    job = uuid.uuid4().hex
    folder = JOBS / job
    folder.mkdir(parents=True, exist_ok=False)
    try:
        source = download(video_url, folder)
        audio = folder / "narration.mp3"
        narration_text = "Olha esse achadinho incrivel para sua casa! Pratico, moderno e vai facilitar demais a sua rotina. Corre no link da bio e garanta o seu antes que esgote!"
        words = await make_voice(narration_text, audio)
        audio_duration = probe_duration(audio)
        duration = min(16.0, max(10.0, audio_duration + 0.2))
        ass = folder / "captions.ass"
        make_ass(ass, words, duration)
        headline_img = folder / "headline.png"
        make_headline(headline_img, headline)
        output = folder / "klebee_video.mp4"
        render(source, audio, ass, headline_img, output, duration)
        return FileResponse(output, media_type="video/mp4", filename="super_robo_klebee_v150.mp4")
    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"ERRO CRITICO NO JOB {job}:\n{err_msg}")
        raise HTTPException(status_code=500, detail=f"Erro na renderizacao: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
