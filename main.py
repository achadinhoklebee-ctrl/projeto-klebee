"""Super Robô Klebee — V165 - FIX OOM - VOLTA ASS LEVE + HEADLINE 135PT PRINT 4"""
from __future__ import annotations
import os, shutil, subprocess, uuid, traceback
from pathlib import Path
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-V165-ASS-FIX-OOM"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1080, 1920, 30
VOICE_DEFAULT = "pt-BR-FranciscaNeural"
RATE_VIBRANTE = "+10%"
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
]

app = FastAPI(title="Super Robô Klebee", version=VERSION)

def binary(name: str) -> str:
    p = shutil.which(name)
    if not p:
        raise RuntimeError(f"Executavel ausente: {name}")
    return p

def run(args: list[str], timeout: int = 400) -> subprocess.CompletedProcess:
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"Falhou ({p.returncode}): {(p.stderr or p.stdout)[-4000:]}")
    return p

def font(size: int):
    for pth in FONT_PATHS:
        if Path(pth).is_file():
            try:
                return ImageFont.truetype(pth, size=size)
            except:
                pass
    return ImageFont.load_default()

def make_headline_print4(path: Path, text: str):
    image = Image.new("RGBA", (W, 650), (0,0,0,0))
    draw = ImageDraw.Draw(image)
    size = 135
    f = font(size)
    words = text.upper().split()
    lines = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip()
        bbox = draw.textbbox((0,0), cand, font=f, stroke_width=18)
        if bbox[2]-bbox[0] <= W-80:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    lines = lines[:3]
    y = 20
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=f, stroke_width=18)
        x = (W - (bbox[2]-bbox[0])) // 2
        draw.text((x+5, y+5), line, font=f, fill="black", stroke_width=18, stroke_fill="black")
        draw.text((x, y), line, font=f, fill="#FFE500", stroke_width=18, stroke_fill="black")
        y += bbox[3]-bbox[1] + 22
    image.save(path)

def ass_time(s: float) -> str:
    n = max(0, round(s*100))
    h,n = divmod(n,360000); m,n = divmod(n,6000); sec,cs = divmod(n,100)
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

def esc_ass(s: str) -> str:
    return s.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")

def make_ass_one_word_70pct(path: Path, words, duration: float):
    # LEGENDA 70% ALTURA = 615px do rodapé (evita link Shopee)
    # 70% de 1920 = 1344 topo = 576 rodapé
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,98,&H0000E5FF,&H0000E5FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,12,2,2,80,80,615,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for w in words:
        s = w["start"]
        e = min(duration, w["end"])
        if e <= s:
            e = s + 0.35
        txt = esc_ass(w["text"])
        events.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Caption,,0,0,0,,{txt}")
    
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")

def download(url: str, folder: Path) -> Path:
    opts = {"format":"bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best","outtmpl":str(folder/"source.%(ext)s"),"noplaylist":True,"quiet":True,"no_warnings":True,"merge_output_format":"mp4"}
    with YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
    cands = [p for p in folder.glob("source.*") if p.is_file() and p.stat().st_size>100_000]
    if not cands:
        raise RuntimeError("Sem video")
    return max(cands, key=lambda p: p.stat().st_size)

def probe_duration(path: Path) -> float:
    p = run([binary("ffprobe"),"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],60)
    try:
        return float(p.stdout.strip())
    except:
        return 10.0

def render_ass_fixed(source, audio, headline, ass_path, output, duration):
    ass_esc = str(ass_path.resolve()).replace("\\","/").replace(":","\\:").replace("'","\\'")
    cmd = [
        binary("ffmpeg"),"-y",
        "-stream_loop","1","-i",str(source),
        "-i",str(audio),
        "-loop","1","-t",f"{duration:.3f}","-i",str(headline),
        "-filter_complex",
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setpts=N/FRAME_RATE/TB[bg];[bg][2:v]overlay=0:35[with_head];[with_head]ass='{ass_esc}'[v];[0:a]volume=0.15[a_music];[1:a]volume=1.25[a_voice];[a_music][a_voice]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a_final]",
        "-map","[v]","-map","[a_final]",
        "-t",f"{duration:.3f}",
        "-c:v","libx264","-preset","ultrafast","-crf","20",
        "-c:a","aac","-b:a","192k",
        str(output)
    ]
    run(cmd,400)

@app.get("/")
def home():
    return HTMLResponse(f"<h1>KLEBEE V165 - ASS FIX OOM</h1><p>Headline 135pt print 4 + Legenda 1 palavra 70% - sem estourar RAM</p><a href='/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA'>GERAR V165</a>")

@app.get("/health")
def health():
    return {"status":"ok","version":VERSION}

@app.get("/render-web")
async def render_web(video_url: str = Query("https://www.tiktok.com/@carey_collections/video/7688751450901597461"), headline: str = Query("ACHADINHO INCRIVEL!"), voice: str = Query("Francisca")):
    job = uuid.uuid4().hex; folder = JOBS/job; folder.mkdir(parents=True)
    try:
        if voice.lower().startswith("anton"):
            voice_id = "pt-BR-AntonioNeural"; rate = "+12%"
        else:
            voice_id = "pt-BR-FranciscaNeural"; rate = "+10%"
        source = download(video_url, folder)
        audio = folder/"narration.mp3"
        txt = "Olha esse achadinho incrivel para sua casa! Pratico, moderno e vai facilitar demais a sua rotina. Corre no link da bio e garanta o seu antes que esgote!"
        tmp = folder/"tmp.mp3"
        comm = edge_tts.Communicate(txt, voice_id, rate=rate)
        ab = bytearray()
        async for ch in comm.stream():
            if ch["type"]=="audio":
                ab.extend(ch["data"])
        with tmp.open("wb") as f:
            f.write(ab)
        audio_dur = probe_duration(tmp)
        duration = min(16.0, max(10.5, audio_dur + 0.3))
        usable = max(0.5, audio_dur - 0.35)
        clean = txt.split()
        time_per = usable / max(1, len(clean))
        comm2 = edge_tts.Communicate(txt, voice_id, rate=rate)
        ab2 = bytearray()
        async for ch in comm2.stream():
            if ch["type"]=="audio":
                ab2.extend(ch["data"])
        with audio.open("wb") as f:
            f.write(ab2)
        words = []
        for i, w in enumerate(clean):
            s = 0.15 + i*time_per; e = s+time_per
            words.append({"text": w, "start": s, "end": e})
        
        ass = folder/"captions.ass"
        make_ass_one_word_70pct(ass, words, duration)
        hl = folder/"headline.png"
        make_headline_print4(hl, headline)
        out = folder/"klebee.mp4"
        render_ass_fixed(source, audio, hl, ass, out, duration)
        return FileResponse(out, media_type="video/mp4", filename="klebee_v165.mp4")
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(500, f"Erro: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
