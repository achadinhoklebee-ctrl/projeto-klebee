"""Super Robô Klebee — V160 - FIX ESTOURO E REPETICAO - TIKTOK VIRAL 3 PALAVRAS"""
from __future__ import annotations
import os, shutil, subprocess, uuid, traceback
from pathlib import Path
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-V160-TIKTOK-3-PALAVRAS"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1080, 1920, 30
VOICE = os.getenv("KLEBEE_TTS_VOICE", "pt-BR-AntonioNeural")
RATE = os.getenv("KLEBEE_TTS_RATE", "+0%")
FONT_PATHS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]

app = FastAPI(title="Super Robô Klebee", version=VERSION)

def binary(name: str) -> str:
    p = shutil.which(name)
    if not p: raise RuntimeError(f"Executavel ausente: {name}")
    return p

def run(args: list[str], timeout: int = 400) -> subprocess.CompletedProcess:
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode: raise RuntimeError(f"Falhou ({p.returncode}): {(p.stderr or p.stdout)[-2500:]}")
    return p

def font(size: int):
    for pth in FONT_PATHS:
        if Path(pth).is_file():
            try: return ImageFont.truetype(pth, size=size)
            except: pass
    return ImageFont.load_default()

def wrap(draw, text, f, max_width):
    lines, cur = [], ""
    for w in text.split():
        cand = f"{cur} {w}".strip()
        if draw.textbbox((0,0), cand, font=f, stroke_width=13)[2] <= max_width:
            cur = cand
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines[:3]

def make_headline(path: Path, text: str):
    image = Image.new("RGBA", (W, 500), (0,0,0,0))
    draw = ImageDraw.Draw(image)
    size = 112
    while size >= 60:
        f = font(size)
        if wrap(draw, text.upper(), f, W-120): break
        size -= 2
    f = font(max(size, 60))
    lines = wrap(draw, text.upper(), f, W-120) or [text.upper()]
    y = 15
    for line in lines:
        box = draw.textbbox((0,0), line, font=f, stroke_width=13)
        x = (W - (box[2]-box[0])) // 2
        draw.text((x,y), line, font=f, fill="#FFE500", stroke_width=13, stroke_fill=(0,0,0,255))
        y += box[3]-box[1]+16
    image.save(path)

def make_caption_png_tiktok(path: Path, window_words: list[str], active_pos_in_window: int):
    """Gera 1 PNG com 3 palavras max, só 1 amarela - SEM ESTOURO"""
    img = Image.new("RGBA", (W, 350), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    f = font(82)
    
    # Mede largura real de cada palavra com stroke para não estourar
    widths = []
    for w in window_words:
        bbox = draw.textbbox((0,0), w+" ", font=f, stroke_width=10)
        widths.append(bbox[2]-bbox[0])
    
    total_w = sum(widths)
    # Se estourar 1080, reduz fonte automaticamente
    if total_w > W-120:
        f = font(68)
        widths=[]
        for w in window_words:
            bbox = draw.textbbox((0,0), w+" ", font=f, stroke_width=10)
            widths.append(bbox[2]-bbox[0])
        total_w = sum(widths)
    
    x = (W - total_w)//2
    y = 80
    
    for i, w in enumerate(window_words):
        is_active = (i == active_pos_in_window)
        color = "#FFE500" if is_active else "#FFFFFF"
        draw.text((x, y), w, font=f, fill=color, stroke_width=10, stroke_fill=(0,0,0,255))
        x += widths[i]
    
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

def render_png_sequence(source, audio, headline, caption_pngs, words, output, duration):
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
        filters.append(f"{last}{input_label}overlay=(W-w)/2:H-360:enable='between(t,{s:.3f},{e:.3f})'[tmp{next_idx}]")
        last = f"[tmp{next_idx}]"; next_idx+=1

    filters.append(f"[0:a]volume=0.18[a_music];[1:a]volume=1.15[a_voice];[a_music][a_voice]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a_final]")
    filter_complex = ";".join(filters)

    cmd = [binary("ffmpeg"),"-y","-stream_loop","1","-i",str(source),"-i",str(audio),"-i",str(headline)]
    for p in caption_pngs: cmd.extend(["-i", str(p)])
    cmd.extend(["-filter_complex", filter_complex, "-map", last, "-map", "[a_final]", "-t", f"{duration:.3f}", "-threads","4","-c:v","libx264","-preset","ultrafast","-crf","20","-c:a","aac","-b:a","192k", str(output)])
    run(cmd,600)

@app.get("/")
def home(): return HTMLResponse(f"<h1>KLEBEE V160 - FIX ESTOURO</h1><a href='/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA'>GERAR V160</a>")

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

        # JANELA DE 3 PALAVRAS COM SENTIDO - PADRÃO TIKTOK
        all_texts = [w["text"] for w in words]
        caption_pngs=[]
        for i in range(len(all_texts)):
            # Pega janela de 3: anterior, atual, próxima
            start = max(0, i-1)
            end = min(len(all_texts), i+2)
            window = all_texts[start:end]
            active_pos = i - start
            
            # Ajusta para sempre ter 3 palavras quando possível para não pular
            if len(window) < 3 and len(all_texts) >= 3:
                if start == 0:
                    window = all_texts[0:3]
                    active_pos = i
                elif end == len(all_texts):
                    window = all_texts[-3:]
                    active_pos = i - (len(all_texts)-3)
            
            p = caps_dir / f"cap_{i:03d}.png"
            make_caption_png_tiktok(p, window, active_pos)
            caption_pngs.append(p)

        hl=folder/"headline.png"; make_headline(hl,headline)
        out=folder/"klebee.mp4"; render_png_sequence(source,audio,hl,caption_pngs,words,out,duration)
        return FileResponse(out, media_type="video/mp4", filename="klebee_v160.mp4")
    except Exception as e:
        print(traceback.format_exc()); raise HTTPException(500,f"Erro: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
