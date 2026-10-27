"""Super Robô Klebee — V159 - 【entity-PREMIERE PRO¦canonical_name=Premiere Pro】 REAL - PNG POR PALAVRA - SEM .ASS"""
from __future__ import annotations
import os, shutil, subprocess, uuid, traceback
from pathlib import Path
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-V159-PNG-PREMIERE"
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
        if draw.textbbox((0,0), cand, font=f, stroke_width=10)[2] <= max_width:
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

def make_caption_png(path: Path, words: list[str], active_idx: int):
    """Gera 1 PNG com frase completa, só active em amarelo"""
    img = Image.new("RGBA", (W, 400), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    f = font(68)
    
    # Monta linhas com quebra inteligente - max 3 palavras por linha para não cortar borda
    text = " ".join(words)
    # Limita a frase para fazer sentido: pega janela de 5 palavras em torno da ativa
    start = max(0, active_idx - 2)
    end = min(len(words), active_idx + 3)
    window = words[start:end]
    
    lines = []
    cur_line = []
    for w in window:
        cur_line.append(w)
        if len(cur_line) >= 4:  # 4 palavras por linha max
            lines.append(cur_line)
            cur_line = []
    if cur_line:
        lines.append(cur_line)
    if len(lines) > 2: lines = lines[:2]  # Max 2 linhas
    
    y = 10
    for line_words in lines:
        # Calcula largura total da linha
        line_text = " ".join(line_words)
        bbox = draw.textbbox((0,0), line_text, font=f, stroke_width=9)
        total_w = bbox[2]-bbox[0]
        x = (W - total_w)//2
        
        for w in line_words:
            global_idx = words.index(w, start) if w in words[start:end] else -1
            # Verifica se é a palavra ativa
            is_active = (window.index(w) + start == active_idx) if w in window else False
            
            # Calcula bbox da palavra
            wb = draw.textbbox((0,0), w+" ", font=f, stroke_width=9)
            ww = wb[2]-wb[0]
            
            color = "#FFE500" if is_active else "#FFFFFF"
            # Desenha com contorno preto grosso estilo TikTok
            draw.text((x, y), w, font=f, fill=color, stroke_width=9, stroke_fill=(0,0,0,255))
            x += ww
        y += 80

    img.save(path)

def esc_filter_path(p: Path) -> str:
    return str(p.resolve()).replace("\\","/").replace(":","\\:").replace("'","\\'")

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
    # Constrói filter_complex com overlays encadeados com enable=between
    # Inputs: 0:v source, 1:a audio, 2:v headline, 3:v cap0, 4:v cap1...
    filters = []
    # Primeiro scale e crop
    filters.append(f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setpts=N/FRAME_RATE/TB[bg]")
    last = "[bg]"
    next_idx = 0
    filters.append(f"{last}[2:v]overlay=0:45[tmp{next_idx}]")
    last = f"[tmp{next_idx}]"
    next_idx+=1

    # Overlays de legenda com tempo
    for i, (png_path, w) in enumerate(zip(caption_pngs, words)):
        s = w["start"]
        e = min(duration, w["end"])
        # Input index para este png = 3 + i
        input_label = f"[{3+i}:v]"
        filters.append(f"{last}{input_label}overlay=(W-w)/2:H-380:enable='between(t,{s:.3f},{e:.3f})'[tmp{next_idx}]")
        last = f"[tmp{next_idx}]"
        next_idx+=1

    # Audio mix
    filters.append(f"[0:a]volume=0.18[a_music];[1:a]volume=1.15[a_voice];[a_music][a_voice]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a_final]")

    filter_complex = ";".join(filters)

    cmd = [binary("ffmpeg"),"-y","-stream_loop","1","-i",str(source),"-i",str(audio),"-i",str(headline)]
    # Adiciona todos os pngs como inputs
    for p in caption_pngs:
        cmd.extend(["-i", str(p)])
    cmd.extend(["-filter_complex", filter_complex, "-map", last, "-map", "[a_final]", "-t", f"{duration:.3f}", "-threads","4","-c:v","libx264","-preset","ultrafast","-crf","20","-c:a","aac","-b:a","192k", str(output)])
    run(cmd,500)

@app.get("/")
def home(): return HTMLResponse(f"<h1>KLEBEE V159 - PNG PREMIERE</h1><a href='/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA'>GERAR V159</a>")

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

        # Gera 1 PNG por palavra com frase com sentido
        all_texts = [w["text"] for w in words]
        caption_pngs=[]
        for i, w in enumerate(words):
            p = caps_dir / f"cap_{i:03d}.png"
            make_caption_png(p, all_texts, i)
            caption_pngs.append(p)

        hl=folder/"headline.png"; make_headline(hl,headline)
        out=folder/"klebee.mp4"; render_png_sequence(source,audio,hl,caption_pngs,words,out,duration)
        return FileResponse(out, media_type="video/mp4", filename="klebee_v159.mp4")
    except Exception as e:
        print(traceback.format_exc()); raise HTTPException(500,f"Erro: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
