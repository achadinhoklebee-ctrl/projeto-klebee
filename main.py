"""Super Robô Klebee — V161 - PREMIERE REAL - 1 PALAVRA GIGANTE - 70% ALTURA - HEADLINE HORMOZI"""
from __future__ import annotations
import os, shutil, subprocess, uuid, traceback
from pathlib import Path
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-V161-PREMIERE-1-WORD-70PCT"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1080, 1920, 30
VOICE = os.getenv("KLEBEE_TTS_VOICE", "pt-BR-AntonioNeural")
RATE = os.getenv("KLEBEE_TTS_RATE", "+0%")
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
]

app = FastAPI(title="Super Robô Klebee", version=VERSION)

def binary(name: str) -> str:
    p = shutil.which(name)
    if not p: raise RuntimeError(f"Executavel ausente: {name}")
    return p

def run(args: list[str], timeout: int = 400) -> subprocess.CompletedProcess:
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode: raise RuntimeError(f"Falhou ({p.returncode}): {(p.stderr or p.stdout)[-2500:]}")
    return p

def font(size: int, bold=True):
    for pth in FONT_PATHS:
        if Path(pth).is_file():
            try: return ImageFont.truetype(pth, size=size)
            except: pass
    return ImageFont.load_default()

def wrap(draw, text, f, max_width, stroke=16):
    lines, cur = [], ""
    for w in text.split():
        cand = f"{cur} {w}".strip()
        if draw.textbbox((0,0), cand, font=f, stroke_width=stroke)[2] <= max_width:
            cur = cand
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines[:3]

def make_headline_hormozi(path: Path, text: str):
    # ESTILO FOTO 4: TODO MUNDO odeia NARRAR VIDEO - extra bold, agressivo
    image = Image.new("RGBA", (W, 550), (0,0,0,0))
    draw = ImageDraw.Draw(image)
    size = 125
    while size >= 70:
        f = font(size)
        if wrap(draw, text.upper(), f, W-100, 16): break
        size -= 2
    f = font(max(size, 70))
    lines = wrap(draw, text.upper(), f, W-100, 16) or [text.upper()]
    y = 20
    for line in lines:
        box = draw.textbbox((0,0), line, font=f, stroke_width=16)
        x = (W - (box[2]-box[0])) // 2
        # Contorno preto ultra grosso + preenchimento amarelo - estilo Hormozi
        draw.text((x,y), line, font=f, fill="#FFE500", stroke_width=16, stroke_fill=(0,0,0,255))
        y += box[3]-box[1]+18
    image.save(path)

def make_caption_one_word(path: Path, word: str):
    """ESTILO FOTO 5: CAPTIONS - 1 palavra gigante amarela, centralizada"""
    img = Image.new("RGBA", (W, 300), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    # Tenta fonte grande, se não couber reduz
    size = 95
    f = font(size)
    bbox = draw.textbbox((0,0), word, font=f, stroke_width=11)
    w_width = bbox[2]-bbox[0]
    
    while w_width > W-100 and size > 50:
        size -= 4
        f = font(size)
        bbox = draw.textbbox((0,0), word, font=f, stroke_width=11)
        w_width = bbox[2]-bbox[0]
    
    x = (W - w_width)//2
    y = 30
    # CAPTIONS style: amarelo com contorno preto grosso
    draw.text((x, y), word, font=f, fill="#FFE500", stroke_width=11, stroke_fill=(0,0,0,255))
    img.save(path)

async def make_voice_and_words_real_time(text: str, audio_path: Path, duration: float):
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    audio_bytes = bytearray()
    async for chunk in comm.stream():
        if chunk["type"] == "audio": audio_bytes.extend(chunk["data"])
    if not audio_bytes: raise RuntimeError("TTS sem audio")
    with audio_path.open("wb") as f: f.write(audio_bytes)
    clean_words = text.split()
    usable_duration = max(0.5, duration - 0.4)
    time_per_word = usable_duration / max(1, len(clean_words))
    words=[]
    for i, w in enumerate(clean_words):
        start = 0.2 + i * time_per_word
        end = start + time_per_word
        words.append({"text": w, "start": start, "end": end})
    return words

def download(url: str, folder: Path) -> Path:
    opts={"format":"bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best","outtmpl":str(folder/"source.%(ext)s"),"noplaylist":True,"quiet":True,"no_warnings":True,"merge_output_format":"mp4"}
    with YoutubeDL(opts) as ydl: ydl.extract_info(url, download=True)
    cands=[p for p in folder.glob("source.*") if p.is_file() and p.stat().st_size>100_000]
    if not cands: raise RuntimeError("Sem video")
    return max(cands, key=lambda p: p.stat().st_size)

def probe_duration(path: Path) -> float:
    p=run([binary("ffprobe"),"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],60)
    try: return float(p.stdout.strip())
    except: return 10.0

def render_one_word_premiere(source, audio, headline, caption_pngs, words, output, duration):
    # ALTURA 70% = 1300px do topo, evita link Shopee
    CAPTION_Y = int(H * 0.68)  # 1305
    
    filters = []
    filters.append(f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setpts=N/FRAME_RATE/TB[bg]")
    last = "[bg]"
    next_idx = 0
    filters.append(f"{last}[2:v]overlay=0:45[tmp{next_idx}]")
    last = f"[tmp{next_idx}]"; next_idx+=1

    for i, (png_path, w) in enumerate(zip(caption_pngs, words)):
        s = w["start"]
        e = min(duration, w["end"])
        input_label = f"[{3+i}:v]"
        filters.append(f"{last}{input_label}overlay=0:{CAPTION_Y}:enable='between(t,{s:.3f},{e:.3f})'[tmp{next_idx}]")
        last = f"[tmp{next_idx}]"; next_idx+=1

    filters.append(f"[0:a]volume=0.18[a_music];[1:a]volume=1.15[a_voice];[a_music][a_voice]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a_final]")
    filter_complex = ";".join(filters)

    cmd = [binary("ffmpeg"),"-y","-stream_loop","1","-i",str(source),"-i",str(audio),"-i",str(headline)]
    for p in caption_pngs: cmd.extend(["-i", str(p)])
    cmd.extend(["-filter_complex", filter_complex, "-map", last, "-map", "[a_final]", "-t", f"{duration:.3f}", "-threads","4","-c:v","libx264","-preset","ultrafast","-crf","20","-c:a","aac","-b:a","192k", str(output)])
    run(cmd,600)

@app.get("/")
def home(): return HTMLResponse(f"<h1>KLEBEE V161 - 1 WORD PREMIERE 70%</h1><a href='/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA'>GERAR V161</a>")

@app.get("/health")
def health(): return {"status":"ok","version":VERSION}

@app.get("/render-web")
async def render_web(video_url: str = Query("https://www.tiktok.com/@carey_collections/video/7688751450901597461"), headline: str = Query("ACHADINHO INCRIVEL!")):
    job=uuid.uuid4().hex; folder=JOBS/job; folder.mkdir(parents=True)
    caps_dir = folder / "caps"; caps_dir.mkdir()
    try:
        source=download(video_url,folder); audio=folder/"narration.mp3"
        txt="Olha esse achadinho incrivel para sua casa! Pratico, moderno e vai facilitar demais a sua rotina. Corre no link da bio e garanta o seu antes que esgote!"
        tmp = folder / "tmp.mp3"
        comm = edge_tts.Communicate(txt, VOICE, rate=RATE)
        ab = bytearray()
        async for ch in comm.stream():
            if ch["type"]=="audio": ab.extend(ch["data"])
        with tmp.open("wb") as f: f.write(ab)
        audio_dur=probe_duration(tmp)
        duration=min(16.0, max(10.5, audio_dur + 0.5))
        words=await make_voice_and_words_real_time(txt,audio,duration)

        caption_pngs=[]
        for i, w in enumerate(words):
            p = caps_dir / f"cap_{i:03d}.png"
            make_caption_one_word(p, w["text"])
            caption_pngs.append(p)

        hl=folder/"headline.png"; make_headline_hormozi(hl,headline)
        out=folder/"klebee.mp4"; render_one_word_premiere(source,audio,hl,caption_pngs,words,out,duration)
        return FileResponse(out, media_type="video/mp4", filename="klebee_v161.mp4")
    except Exception as e:
        print(traceback.format_exc()); raise HTTPException(500,f"Erro: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
