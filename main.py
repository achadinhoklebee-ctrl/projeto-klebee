"""Super Robô Klebee — V148 - Legenda Premiere Pro + Headline com Fundo Preto e Borda Amarela"""
from __future__ import annotations
import os, shutil, subprocess, uuid, traceback
from pathlib import Path
from typing import Any
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-PRO-V148-PREMIERE-FIX"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1080, 1920, 30
VOICE = os.getenv("KLEBEE_TTS_VOICE", "pt-BR-AntonioNeural")
RATE = os.getenv("KLEBEE_TTS_RATE", "+15%")
FONT_PATHS = [
    os.getenv("KLEBEE_FONT", ""), 
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
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
        if draw.textbbox((0, 0), candidate, font=f, stroke_width=10)[2] <= max_width:
            current = candidate
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines[:3]

def make_headline(path: Path, text: str):
    # Cria uma tarja/fundo preto sólido para destacar a headline com máxima conversão
    image = Image.new("RGBA", (W, 520), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    size = 110
    while size >= 65:
        f = font(size)
        lines = wrap(draw, text.upper(), f, W - 120)
        if lines: break
        size -= 2
    f = font(max(size, 65))
    lines = wrap(draw, text.upper(), f, W - 120) or [text.upper()[:32]]
    
    # Calcula dimensões do texto para desenhar o fundo preto sólido com margem
    line_heights = [draw.textbbox((0, 0), line, font=f, stroke_width=12)[3] for line in lines]
    total_text_h = sum(line_heights) + 18 * (len(lines) - 1)
    
    bg_box_y0 = 30
    bg_box_y1 = bg_box_y0 + total_text_h + 60
    bg_box_x0 = 60
    bg_box_x1 = W - 60
    
    # Desenha o retângulo preto sólido de fundo com borda amarela
    draw.rounded_rectangle(
        [bg_box_x0, bg_box_y0, bg_box_x1, bg_box_y1],
        radius=24,
        fill=(0, 0, 0, 230),        # Fundo preto quase opaco
        outline=(255, 229, 0, 255), # Borda amarela (#FFE500)
        width=6
    )
    
    y = bg_box_y0 + 30
    for line in lines:
        box = draw.textbbox((0, 0), line, font=f, stroke_width=12)
        x = (W - (box[2] - box[0])) // 2
        # Texto amarelo com contorno preto grosso
        draw.text((x, y), line, font=f, fill="#FFE500", stroke_width=12, stroke_fill=(0, 0, 0, 255))
        y += draw.textbbox((0, 0), line, font=f, stroke_width=12)[3] + 18
        
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
        audio_duration = max(3.0, len(audio_bytes) / 16000.0)
        step = audio_duration / max(1, len(clean_words))
        for i, w in enumerate(clean_words):
            words.append({"text": w, "start": i * step, "end": (i+1)*step})
    return words

def make_ass(path: Path, words: list[dict[str, Any]], duration: float):
    # V148: Legenda Maior (92pt), Centralizada e com tag \k de Karaokê fluido
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,92,&H00FFFFFF,&H0000E5FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,10,3,5,60,60,680,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    groups = []
    cur = []
    for w in words:
        cur.append(w)
        is_long = (w["end"] - cur[0]["start"]) > 1.4
        is_many = len(cur) >= 5
        is_pause = len(cur) > 1 and (w["start"] - cur[-2]["end"]) > 0.35
        if is_long or is_many or is_pause:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)

    events = []
    for group in groups:
        g_start = group[0]["start"]
        g_end = min(duration, group[-1]["end"] + 0.35)
        line_text = ""
        for w in group:
            k_dur = int(max(0.15, w["end"] - w["start"]) * 100)
            line_text += f"{{\\k{k_dur}}}{esc_ass(w['text'])} "
        events.append(f"Dialogue: 0,{ass_time(g_start)},{ass_time(g_end)},Caption,,0,0,0,,{line_text.strip()}")
        
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")

def download(url: str, folder: Path) -> Path:
    opts = {
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
        "outtmpl": str(folder / "source.%(ext)s"),
        "noplaylist": True, "quiet": True, "no_warnings": True,
        "merge_output_format": "mp4", "retries": 2, "socket_timeout": 25
    }
    with YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
    cands = [p for p in folder.glob("source.*") if p.is_file() and p.stat().st_size > 100_000]
    if not cands: raise RuntimeError("Download sem arquivo válido.")
    return max(cands, key=lambda p: p.stat().st_size)

def probe_duration(path: Path) -> float:
    p = run([binary("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], 60)
    return float(p.stdout.strip())

def render(source: Path, audio: Path, ass: Path, headline: Path, output: Path, duration: float):
    ass_path = str(ass.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    headline_path = str(headline.resolve()).replace("\\", "/")
    cmd = [
        binary("ffmpeg"), "-y",
        "-i", str(source), "-i", str(audio), "-i", headline_path,
        "-filter_complex", (
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}[bg]; "
            f"[bg][2:v]overlay=0:20[with_headline]; "
            f"[with_headline]ass='{ass_path}'[v]; "
            f"[0:a]volume=0.20[a_music]; [1:a]volume=1.1[a_voice]; "
            f"[a_music][a_voice]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[a_final]"
        ),
        "-map", "[v]", "-map", "[a_final]", "-t", f"{duration:.3f}",
        "-threads", "4", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "21",
        "-c:a", "aac", "-b:a", "192k", "-shortest", str(output)
    ]
    run(cmd, timeout=400)

@app.get("/", response_class=HTMLResponse)
def home():
    return f"""<html><body style="background:#0f172a;color:#fff;text-align:center;padding:60px"><h1>🚀 Klebee V148 - Fundo Preto & Legenda Gigante</h1><a style="background:#22c55e;color:white;padding:18px 36px;border-radius:10px;text-decoration:none" href="/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA">GERAR V148</a></body></html>"""

@app.get("/health")
def health(): return {"status": "ok", "version": VERSION}

@app.get("/render-web")
async def render_web(video_url: str = Query(...), headline: str = Query("ACHADINHO INCRÍVEL!")):
    job = uuid.uuid4().hex
    folder = JOBS / job
    folder.mkdir(parents=True, exist_ok=False)
    try:
        source = download(video_url, folder)
        audio = folder / "narration.mp3"
        narration_text = "Olha esse achadinho incrível para sua casa! Prático, moderno e vai facilitar demais a sua rotina. Corre no link da bio e garanta o seu antes que esgote!"
        words = await make_voice(narration_text, audio)
        audio_duration = probe_duration(audio)
        duration = min(16.0, max(10.0, audio_duration + 0.2))
        ass = folder / "captions.ass"
        make_ass(ass, words, duration)
        headline_img = folder / "headline.png"
        make_headline(headline_img, headline)
        output = folder / "klebee_video.mp4"
        render(source, audio, ass, headline_img, output, duration)
        return FileResponse(output, media_type="video/mp4", filename="klebee_v148.mp4")
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
