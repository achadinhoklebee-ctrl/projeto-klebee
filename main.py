"""Super Robô Klebee — V151 - MOTOR PREMIERE PRO REAL - SEM ASS KARAOKE"""
from __future__ import annotations
import os
import shutil
import subprocess
import uuid
import traceback
import re
from pathlib import Path
from typing import Any
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-V151-PREMIERE-REAL"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1080, 1920, 30
VOICE = os.getenv("KLEBEE_TTS_VOICE", "pt-BR-AntonioNeural")
RATE = os.getenv("KLEBEE_TTS_RATE", "+15%")
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
]

app = FastAPI(title="Super Robô Klebee", version=VERSION)

def binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Executavel ausente: {name}")
    return path

def run(args: list[str], timeout: int = 400) -> subprocess.CompletedProcess:
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"Falhou ({p.returncode}): {(p.stderr or p.stdout)[-2500:]}")
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
        if draw.textbbox((0, 0), cand, font=f, stroke_width=13)[2] <= max_width:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:3]

def make_headline(path: Path, text: str):
    image = Image.new("RGBA", (W, 480), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    size = 110
    while size >= 60:
        f = font(size)
        if wrap(draw, text.upper(), f, W - 120):
            break
        size -= 2
    f = font(max(size, 60))
    lines = wrap(draw, text.upper(), f, W - 120) or [text.upper()]
    y = 15
    for line in lines:
        box = draw.textbbox((0, 0), line, font=f, stroke_width=13)
        x = (W - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=f, fill="#FFE500", stroke_width=13, stroke_fill=(0, 0, 0, 255))
        y += box[3] - box[1] + 16
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
        raise RuntimeError("TTS sem audio")
    with path.open("wb") as f:
        f.write(audio_bytes)
    if not words:
        clean = text.split()
        dur = max(3.0, len(audio_bytes) / 16000.0)
        step = dur / max(1, len(clean))
        words = [{"text": w, "start": i * step, "end": (i + 1) * step} for i, w in enumerate(clean)]
    return words

def make_ass_premiere(path: Path, words: list[dict[str, Any]], duration: float):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,86,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,10,2,5,80,80,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # 1. Quebra por frase para NAO misturar frases
    sentences = []
    cur_sentence = []
    for w in words:
        cur_sentence.append(w)
        if w["text"].endswith((".", "!", "?", ",")) or (len(cur_sentence) > 1 and w["start"] - cur_sentence[-2]["end"] > 0.5):
            sentences.append(cur_sentence)
            cur_sentence = []
    if cur_sentence:
        sentences.append(cur_sentence)

    events = []
    for sentence in sentences:
        # 2. Quebra a frase em blocos de 3 palavras (padrao TikTok)
        for i in range(0, len(sentence), 3):
            block = sentence[i:i+3]
            if not block:
                continue
            block_text = " ".join([esc_ass(x["text"]) for x in block])
            # 3. Para cada palavra do bloco, cria um dialogo SEQUENCIAL
            for idx, active_word in enumerate(block):
                s = active_word["start"]
                # Fim = inicio da proxima palavra, ou fim do bloco + 0.2
                if idx + 1 < len(block):
                    e = block[idx+1]["start"]
                else:
                    # Ultima palavra do bloco segura mais tempo
                    if i + 3 < len(sentence):
                        e = sentence[i+3]["start"] - 0.05
                    else:
                        e = min(duration, active_word["end"] + 0.35)
                e = max(s + 0.15, e)
                # Monta o texto com a palavra ativa em amarelo
                parts = []
                for j, w in enumerate(block):
                    token = esc_ass(w["text"])
                    if j == idx:
                        parts.append(f"{{\\c&H00E5FF&\\b1}}{token}{{\\c&HFFFFFF&\\b0}}")
                    else:
                        parts.append(token)
                line = " ".join(parts)
                # Quebra em 2 linhas se necessario (visual)
                if len(block) > 2:
                    # Forca quebra visual no ASS com \\N
                    if len(parts) == 3:
                        line = f"{parts[0]} {parts[1]}\\N{parts[2]}"
                events.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Caption,,0,0,0,,{line}")

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
        raise RuntimeError("Sem video valido")
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
            f"[0:a]volume=0.20[a_music]; "
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
    <html><head><meta charset="UTF-8"><title>Klebee V151</title>
    <style>body{background:#0f172a;color:#fff;font-family:Arial;text-align:center;padding:60px} .card{background:#1e293b;padding:40px;border-radius:16px;display:inline-block} .btn{background:#22c55e;color:white;padding:18px 36px;border-radius:10px;text-decoration:none;font-weight:bold}</style>
    </head><body><div class="card"><h1>KLEBEE V151 - PREMIERE REAL</h1><p>Sem fundo preto + Legenda sem misturar frases</p>
    <a class="btn" href="/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA">GERAR V151</a></div></body></html>
    """

@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION}

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
        make_ass_premiere(ass, words, duration)
        headline_img = folder / "headline.png"
        make_headline(headline_img, headline)
        output = folder / "klebee_video.mp4"
        render(source, audio, ass, headline_img, output, duration)
        return FileResponse(output, media_type="video/mp4", filename="klebee_v151.mp4")
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
