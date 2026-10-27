"""Super Robô Klebee — V173 - RANSOM NOTE VIRAL - IGUAL PRINT QUANTO TEMPO VOCE PERDE"""
from __future__ import annotations
import os, shutil, subprocess, uuid, traceback, time, random
from pathlib import Path
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-V173-RANSOM-NOTE"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920
VOICE = "pt-BR-FranciscaNeural"
RATE = "+10%"

# PALETA RANSOM NOTE igual print: amarelo, rosa, branco, preto, azul, verde claro
PALETTE = [
    ("#FFEB3B", "black"),  # amarelo fundo preto texto
    ("#E91E63", "white"),  # rosa fundo branco texto
    ("#FFFFFF", "black"),  # branco fundo preto texto
    ("#000000", "white"),  # preto fundo branco texto
    ("#03A9F4", "white"),  # azul claro
    ("#FF9800", "black"),  # laranja
    ("#4CAF50", "white"),  # verde
    ("#F44336", "white"),  # vermelho
]

FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
]

app = FastAPI(title="Super Robô Klebee", version=VERSION)

def binary(n: str) -> str:
    p = shutil.which(n)
    if not p:
        raise RuntimeError(f"Sem {n}")
    return p

def run(args, timeout=400):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        err = (p.stderr or p.stdout)[-2000:]
        raise RuntimeError(f"Erro {p.returncode}: {err}")
    return p

def font(sz: int):
    for fp in FONTS:
        if Path(fp).is_file():
            try:
                return ImageFont.truetype(fp, size=sz)
            except:
                pass
    return ImageFont.load_default()

def make_ransom_word(path: Path, word: str, is_headline=False):
    # RANSOM NOTE: cada letra com fundo colorido e torta
    size = 110 if is_headline else 95
    img_w = W
    img_h = 350 if not is_headline else 220
    img = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
    
    f = font(size if not is_headline else 85)
    
    # Calcula largura total com rotação
    total_w = 0
    letters = list(word.upper())
    for letter in letters:
        if letter.strip() == "":
            total_w += 20
        else:
            bb = ImageDraw.Draw(Image.new("RGBA",(1,1))).textbbox((0,0), letter, font=f)
            total_w += (bb[2]-bb[0]) + 8
    
    x = (W - total_w) // 2
    y = 40 if not is_headline else 20
    
    for letter in letters:
        if letter.strip() == "":
            x += 20
            continue
        
        # Cor aleatória da paleta igual print QUANTO TEMPO...
        bg_color, txt_color = random.choice(PALETTE)
        
        # Cria letra com fundo
        bb = ImageDraw.Draw(Image.new("RGBA",(1,1))).textbbox((0,0), letter, font=f)
        lw = bb[2]-bb[0] + 16
        lh = bb[3]-bb[1] + 14
        
        letter_img = Image.new("RGBA", (lw, lh), (0,0,0,0))
        ld = ImageDraw.Draw(letter_img)
        # Fundo colorido
        ld.rectangle([0,0,lw,lh], fill=bg_color)
        # Texto
        ld.text((8, 4), letter, font=f, fill=txt_color)
        
        # Rotação leve -8° a +8° igual print
        angle = random.uniform(-8, 8)
        rotated = letter_img.rotate(angle, resample=Image.BICUBIC, expand=True)
        
        # Cola na imagem principal com offset aleatório vertical -3 a +3
        y_offset = y + random.randint(-4, 4)
        img.alpha_composite(rotated, (x, y_offset))
        
        x += lw - 4  # Sobrepõe levemente igual recorte
    
    img.save(path)

def make_headline_ransom(path: Path, text: str):
    # HEADLINE RANSOM: 3 linhas no topo, cada palavra com estilo recorte
    img = Image.new("RGBA", (W, 750), (0,0,0,0))
    
    words = text.upper().split()[:6]  # Max 6 palavras
    lines = []
    cur = []
    for w in words:
        cur.append(w)
        if len(cur) >= 2:
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    lines = lines[:3]
    
    y = 20
    for line_words in lines:
        line_text = " ".join(line_words)
        # Cria imagem da linha
        line_img_path = path.parent / f"line_{y}.png"
        make_ransom_word(line_img_path, line_text, is_headline=True)
        line_img = Image.open(line_img_path)
        # Cola centralizado com rotação leve da linha toda
        angle = random.uniform(-2, 2)
        rotated_line = line_img.rotate(angle, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(rotated_line, (0, y))
        y += 180
        try:
            line_img_path.unlink()
        except:
            pass
    
    img.save(path)

def ass_time(s: float) -> str:
    n = max(0, round(s*100))
    h,n = divmod(n,360000); m,n = divmod(n,6000); sec,cs = divmod(n,100)
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

def esc(s: str) -> str:
    return s.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")

def make_ass_ransom_70pct(path: Path, words, duration: float):
    # Usa PNGs, não ASS, para ransom note - mas mantém timing
    # Vamos gerar ASS vazio, pois usaremos PNGs para legenda
    header = """[Script Info]
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: C,DejaVu Sans,1,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,0,2,80,80,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    path.write_text(header + "\n", encoding="utf-8")

def download(url: str, folder: Path) -> Path:
    opts = {"format":"bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best","outtmpl":str(folder/"source.%(ext)s"),"noplaylist":True,"quiet":True,"no_warnings":True,"merge_output_format":"mp4"}
    with YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
    cands = [p for p in folder.glob("source.*") if p.is_file() and p.stat().st_size>50000]
    if not cands:
        raise RuntimeError("Sem video")
    return max(cands, key=lambda p: p.stat().st_size)

def probe(p: Path) -> float:
    r = run([binary("ffprobe"),"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(p)],60)
    try:
        return float(r.stdout.strip())
    except:
        return 9.0

async def get_words_zero_delay(text: str, audio_path: Path):
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    audio_bytes = bytearray()
    raw_words = []
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            st = float(chunk.get("offset",0))/10_000_000
            dur = float(chunk.get("duration",0))/10_000_000
            w = str(chunk.get("text","")).strip()
            if w:
                raw_words.append({"text": w, "start": st, "raw_end": st+dur})
    if not audio_bytes:
        raise RuntimeError("TTS sem audio")
    with audio_path.open("wb") as f:
        f.write(audio_bytes)
    if not raw_words:
        clean = text.split()
        tpw = 9.0 / max(1, len(clean))
        return [{"text": w, "start": i*tpw, "end": (i+1)*tpw} for i,w in enumerate(clean)], 9.0
    
    last_raw = max(w["raw_end"] for w in raw_words)
    audio_dur = probe(audio_path)
    target_end = max(0.5, audio_dur - 0.02)
    scale = target_end / max(0.1, last_raw)
    words = []
    for w in raw_words:
        s = w["start"] * scale + 0.05
        e = w["raw_end"] * scale + 0.05
        if e - s < 0.30:
            e = s + 0.30
        words.append({"text": w["text"], "start": s, "end": e})
    return words, audio_dur

def render_ransom(source, audio, headline, caption_pngs, words, out, dur):
    # 70% altura = 615px do rodapé já definido, mas agora PNGs ransom
    CAPTION_Y = int(H * 0.68)
    filters = []
    filters.append(f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setpts=N/FRAME_RATE/TB[bg]")
    last = "[bg]"
    idx = 0
    filters.append(f"{last}[2:v]overlay=0:30[tmp{idx}]")
    last = f"[tmp{idx}]"; idx+=1
    for i, w in enumerate(words):
        s = w["start"]; e = min(dur, w["end"])
        filters.append(f"{last}[{3+i}:v]overlay=(W-w)/2:{CAPTION_Y}:enable='between(t,{s:.3f},{e:.3f})'[tmp{idx}]")
        last = f"[tmp{idx}]"; idx+=1
    filters.append(f"[1:a]volume=1.25[av];[0:a]volume=0.15[am];[av][am]amix=inputs=2:duration=first:dropout_transition=0[a]")
    fc = ";".join(filters)
    cmd = [binary("ffmpeg"),"-y","-threads","2","-stream_loop","1","-i",str(source),"-i",str(audio),"-i",str(headline)]
    for p in caption_pngs:
        cmd.extend(["-i", str(p)])
    cmd.extend(["-filter_complex", fc, "-map", last, "-map", "[a]", "-t", f"{dur:.2f}", "-threads","2","-c:v","libx264","-preset","ultrafast","-crf","26","-x264-params","threads=2","-c:a","aac","-b:a","128k", str(out)])
    run(cmd,500)

def clean():
    try:
        for d in JOBS.glob("*"):
            if d.is_dir() and time.time()-d.stat().st_mtime>900:
                shutil.rmtree(d, ignore_errors=True)
    except:
        pass

@app.get("/")
def home():
    return HTMLResponse("<h1>V173 - RANSOM NOTE VIRAL</h1><p>Igual print QUANTO TEMPO VOCE PERDE - 70% altura</p><a href='/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA'>GERAR V173</a>")

@app.get("/health")
def health():
    return {"status":"ok","version":VERSION}

@app.get("/render-web")
async def render_web(video_url: str = Query("https://www.tiktok.com/@carey_collections/video/7688751450901597461"), headline: str = Query("ACHADINHO INCRIVEL!")):
    clean()
    job = uuid.uuid4().hex; folder = JOBS/job; folder.mkdir(parents=True)
    caps_dir = folder/"caps"; caps_dir.mkdir()
    try:
        src = download(video_url, folder)
        audio = folder/"narr.mp3"
        txt = "Olha esse achadinho incrivel para sua casa! Pratico, moderno e vai facilitar demais a sua rotina. Corre no link da bio e garanta o seu antes que esgote!"
        tmp = folder/"tmp.mp3"
        words, ad = await get_words_zero_delay(txt, tmp)
        dur = ad + 0.12
        import shutil
        shutil.copy(tmp, audio)
        last = max(w["end"] for w in words)
        scale = (ad - 0.02) / max(0.1, last-0.05)
        final_words = []
        for w in words:
            s = (w["start"]-0.05)*scale + 0.05
            e = (w["end"]-0.05)*scale + 0.05
            final_words.append({"text": w["text"], "start": s, "end": e})
        
        # Gera legenda ransom 1 palavra por vez
        caps = []
        for i, w in enumerate(final_words):
            p = caps_dir/f"cap_{i:03d}.png"
            make_ransom_word(p, w["text"], is_headline=False)
            caps.append(p)
        
        hl = folder/"head.png"
        make_headline_ransom(hl, headline)
        
        out = folder/"final.mp4"
        render_ransom(src, audio, hl, caps, final_words, out, dur)
        return FileResponse(out, media_type="video/mp4", filename="klebee_v173.mp4")
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(500, f"Erro: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
