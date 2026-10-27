"""Super Robô Klebee — V174 - RANSOM LEGENDA FIX CROP + HEADLINE PILULA 【entity-HORMOZI¦canonical_name=Alex Hormozi】"""
from __future__ import annotations
import os, shutil, subprocess, uuid, traceback, time, random
from pathlib import Path
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-V174-HORMOZI"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920
VOICE = "pt-BR-FranciscaNeural"
RATE = "+10%"
SHOPEE_ORANGE = "#FF6B00"

PALETTE = [
    ("#FFEB3B", "black"),
    ("#E91E63", "white"),
    ("#FFFFFF", "black"),
    ("#000000", "white"),
    ("#03A9F4", "white"),
    ("#FF9800", "black"),
    ("#4CAF50", "white"),
]

FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]

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

def make_ransom_word_fix_crop(path: Path, word: str):
    # FIX CROP: canvas 520px + margem 30px na letra
    f = font(105)
    img = Image.new("RGBA", (W, 520), (0,0,0,0))
    letters = list(word.upper())
    # calcula largura
    total_w = 0
    bbs = []
    for lt in letters:
        if lt.strip() == "":
            bbs.append(None); total_w += 18
        else:
            bb = ImageDraw.Draw(Image.new("RGBA",(1,1))).textbbox((0,0), lt, font=f)
            w = bb[2]-bb[0]
            bbs.append(w)
            total_w += w + 10
    x = (W - total_w)//2
    y_base = 160  # centro do canvas 520
    
    for idx, lt in enumerate(letters):
        if lt.strip() == "":
            x+=18; continue
        bg, txt = random.choice(PALETTE)
        w_est = bbs[idx]
        lw = w_est + 36
        lh = 110
        li = Image.new("RGBA", (lw, lh), (0,0,0,0))
        ld = ImageDraw.Draw(li)
        ld.rectangle([0,0,lw,lh], fill=bg)
        ld.text((18, 14), lt, font=f, fill=txt)
        ang = random.uniform(-7, 7)
        rot = li.rotate(ang, resample=Image.BICUBIC, expand=True)
        y_off = y_base + random.randint(-8,8) - rot.height//2
        img.alpha_composite(rot, (x, y_off))
        x += lw - 8
    img.save(path)

def make_headline_pilula_hormozi(path: Path, text: str):
    # HEADLINE QUE IMPRESSIONA: 3 PILULAS HORMOZI
    # ACHADINHO (preta + laranja) / QUE FACILITA (amarela + preto) / SUA VIDA (branca + preto)
    img = Image.new("RGBA", (W, 800), (0,0,0,0))
    
    parts = text.upper().split()
    # força 3 linhas bonitas
    if len(parts) <=2:
        l1 = " ".join(parts[:1])
        l2 = " ".join(parts[1:3]) if len(parts)>1 else "QUE FACILITA"
        l3 = "SUA VIDA"
    else:
        l1 = parts[0]  # ACHADINHO
        l2 = " ".join(parts[1:3])  # QUE FACILITA
        l3 = " ".join(parts[3:5]) if len(parts)>3 else "SUA VIDA"
    lines = [(l1, SHOPEE_ORANGE, "black"), (l2, "black", "#FFEB3B"), (l3, "black", "white")]
    
    y = 18
    for i, (line, txt_color, bg_color) in enumerate(lines):
        fsize = 135 if i==0 else (78 if i==1 else 85)
        f = font(fsize)
        # mede
        dummy = ImageDraw.Draw(Image.new("RGBA",(1,1)))
        bb = dummy.textbbox((0,0), line, font=f, stroke_width=12)
        tw = bb[2]-bb[0] + 80
        th = bb[3]-bb[1] + 40
        pill = Image.new("RGBA", (tw+30, th+20), (0,0,0,0))
        pd = ImageDraw.Draw(pill)
        # sombra dupla
        pd.rounded_rectangle([8,12,tw+22,th+14], radius=18, fill="black")
        pd.rounded_rectangle([0,0,tw+14,th+6], radius=18, fill=bg_color)
        pd.text((15,8), line, font=f, fill=txt_color, stroke_width=12, stroke_fill="black" if bg_color!="black" else "#000000")
        # rotação leve -2 / +2 / -1
        ang = [-2.2, 2.0, -1.2][i]
        rot = pill.rotate(ang, resample=Image.BICUBIC, expand=True)
        x = (W - rot.width)//2
        img.alpha_composite(rot, (x, y))
        y += rot.height - 8
    img.save(path)

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

async def get_words(text: str, audio_path: Path):
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    audio_bytes = bytearray(); raw=[]
    async for chunk in comm.stream():
        if chunk["type"]=="audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"]=="WordBoundary":
            st = float(chunk.get("offset",0))/10_000_000
            dur = float(chunk.get("duration",0))/10_000_000
            w = str(chunk.get("text","")).strip()
            if w:
                raw.append({"text":w,"start":st,"raw_end":st+dur})
    if not audio_bytes:
        raise RuntimeError("TTS sem audio")
    with audio_path.open("wb") as f:
        f.write(audio_bytes)
    if not raw:
        clean=text.split(); tpw=9.0/max(1,len(clean))
        return [{"text":w,"start":i*tpw,"end":(i+1)*tpw} for i,w in enumerate(clean)], 9.0
    last_raw=max(w["raw_end"] for w in raw)
    ad=probe(audio_path)
    target=max(0.5, ad-0.02)
    scale=target/max(0.1, last_raw)
    words=[]
    for w in raw:
        s=w["start"]*scale+0.05
        e=w["raw_end"]*scale+0.05
        if e-s<0.32:
            e=s+0.32
        words.append({"text":w["text"],"start":s,"end":e})
    return words, ad

def render(source, audio, headline, caps, words, out, dur):
    CAPTION_Y = int(H*0.68)
    filters=[f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setpts=N/FRAME_RATE/TB[bg]"]
    last="[bg]"; idx=0
    filters.append(f"{last}[2:v]overlay=0:18[tmp{idx}]"); last=f"[tmp{idx}]"; idx+=1
    for i,w in enumerate(words):
        s=w["start"]; e=min(dur,w["end"])
        filters.append(f"{last}[{3+i}:v]overlay=(W-w)/2:{CAPTION_Y}:enable='between(t,{s:.3f},{e:.3f})'[tmp{idx}]")
        last=f"[tmp{idx}]"; idx+=1
    filters.append("[1:a]volume=1.25[av];[0:a]volume=0.15[am];[av][am]amix=inputs=2:duration=first:dropout_transition=0[a]")
    fc=";".join(filters)
    cmd=[binary("ffmpeg"),"-y","-threads","2","-stream_loop","1","-i",str(source),"-i",str(audio),"-i",str(headline)]
    for p in caps:
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
    return HTMLResponse("<h1>V174 - PILULA HORMOZI + RANSOM FIX</h1><a href='/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA'>GERAR V174</a>")

@app.get("/health")
def health():
    return {"status":"ok","version":VERSION}

@app.get("/render-web")
async def render_web(video_url: str = Query("https://www.tiktok.com/@carey_collections/video/7688751450901597461"), headline: str = Query("ACHADINHO INCRIVEL!")):
    clean()
    job=uuid.uuid4().hex; folder=JOBS/job; folder.mkdir(parents=True)
    caps_dir=folder/"caps"; caps_dir.mkdir()
    try:
        src=download(video_url, folder)
        audio=folder/"narr.mp3"
        txt="Olha esse achadinho incrivel para sua casa! Pratico, moderno e vai facilitar demais a sua rotina. Corre no link da bio e garanta o seu antes que esgote!"
        tmp=folder/"tmp.mp3"
        words, ad=await get_words(txt, tmp)
        dur=ad+0.12
        import shutil
        shutil.copy(tmp, audio)
        last=max(w["end"] for w in words)
        scale=(ad-0.02)/max(0.1, last-0.05)
        final=[]
        for w in words:
            s=(w["start"]-0.05)*scale+0.05
            e=(w["end"]-0.05)*scale+0.05
            final.append({"text":w["text"],"start":s,"end":e})
        caps=[]
        for i,w in enumerate(final):
            p=caps_dir/f"cap_{i:03d}.png"
            make_ransom_word_fix_crop(p, w["text"])
            caps.append(p)
        hl=folder/"head.png"
        make_headline_pilula_hormozi(hl, headline)
        out=folder/"final.mp4"
        render(src, audio, hl, caps, final, out, dur)
        return FileResponse(out, media_type="video/mp4", filename="klebee_v174.mp4")
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(500, f"Erro: {e}")

if __name__=="__main__":
    import uvicorn
    port=int(os.environ.get("PORT",8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
