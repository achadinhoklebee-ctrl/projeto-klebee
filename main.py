"""Super Robô Klebee — V176 - HEADLINE RANSOM 3 PILULAS COLORIDAS + SYNC ZERO"""
from __future__ import annotations
import os, shutil, subprocess, uuid, traceback, time, random
from pathlib import Path
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-V176-FINAL"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920
VOICE = "pt-BR-FranciscaNeural"
RATE = "+10%"

PALETTE = [("#FFEB3B","black"),("#FF6B00","white"),("#FFFFFF","black"),("#000000","white"),("#03A9F4","white"),("#E91E63","white"),("#4CAF50","white")]

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

def make_ransom_word(path: Path, word: str, fsize=72, canvas_h=600):
    f = font(fsize)
    img = Image.new("RGBA", (W, canvas_h), (0,0,0,0))
    letters = list(word.upper())
    ws=[]; total=0
    dummy = ImageDraw.Draw(Image.new("RGBA",(1,1)))
    for lt in letters:
        if lt.strip()=="":
            ws.append(14); total+=14
        else:
            bb=dummy.textbbox((0,0), lt, font=f)
            w=bb[2]-bb[0]
            ws.append(w); total+=w+6
    x=(W-total)//2
    y_center=canvas_h//2
    for i,lt in enumerate(letters):
        if lt.strip()=="":
            x+=14; continue
        bg,txt = random.choice(PALETTE)
        lw=ws[i]+22; lh=88 if fsize<=80 else 110
        li=Image.new("RGBA",(lw,lh),(0,0,0,0))
        ld=ImageDraw.Draw(li)
        ld.rectangle([0,0,lw,lh], fill=bg)
        ld.text((11,10), lt, font=f, fill=txt)
        ang=random.uniform(-6,6)
        rot=li.rotate(ang, resample=Image.BICUBIC, expand=True)
        y_off=y_center-rot.height//2+random.randint(-5,5)
        y_off=max(5, min(y_off, canvas_h-rot.height-5))
        img.alpha_composite(rot,(x,y_off))
        x+=lw-6
    img.save(path)

def make_headline_ransom_3_pills(path: Path, text: str):
    # 3 PILULAS TODAS COM FUNDO COLORIDO + LETRA RANSOM QUE RETEM ATENÇÃO
    img = Image.new("RGBA", (W, 820), (0,0,0,0))
    parts = text.upper().split()
    l1 = parts[0] if parts else "ACHADINHO"
    l2 = " ".join(parts[1:3]) if len(parts)>2 else "QUE FACILITA"
    l3 = " ".join(parts[3:5]) if len(parts)>3 else "SUA VIDA"
    lines = [l1,l2,l3]
    # Cores de fundo das pilulas - todas coloridas igual você pediu
    pill_colors = ["#FFEB3B", "#FF6B00", "#FFFFFF"]  # amarelo, laranja, branco
    y=15
    for idx, line in enumerate(lines):
        # Cria linha ransom 85pt
        tmp_path = path.parent / f"hl_tmp_{idx}.png"
        make_ransom_word(tmp_path, line, fsize=88, canvas_h=180)
        line_img = Image.open(tmp_path)
        # Cria pilula atrás
        tw = line_img.width
        # corta espaço vazio para pilula justa
        bbox = line_img.getbbox()
        if bbox:
            line_cropped = line_img.crop(bbox)
        else:
            line_cropped = line_img
        pill_w = line_cropped.width + 60
        pill_h = line_cropped.height + 24
        pill = Image.new("RGBA", (pill_w, pill_h), (0,0,0,0))
        pd = ImageDraw.Draw(pill)
        pd.rounded_rectangle([5,7,pill_w-1,pill_h-3], radius=18, fill=(0,0,0,200))
        pd.rounded_rectangle([0,0,pill_w-6,pill_h-8], radius=18, fill=pill_colors[idx])
        # centraliza ransom dentro da pilula
        px = (pill_w - line_cropped.width)//2
        py = (pill_h - line_cropped.height)//2 - 4
        pill.alpha_composite(line_cropped, (px, py))
        ang = [-2.2, 1.9, -0.9][idx]
        rot = pill.rotate(ang, resample=Image.BICUBIC, expand=True)
        x = (W - rot.width)//2
        img.alpha_composite(rot, (x, y))
        y += rot.height - 8
        try:
            tmp_path.unlink()
        except:
            pass
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

async def get_words_sync_zero(text: str, audio_path: Path):
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    audio_bytes=bytearray(); raw=[]
    async for chunk in comm.stream():
        if chunk["type"]=="audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"]=="WordBoundary":
            st=float(chunk.get("offset",0))/10_000_000
            dur=float(chunk.get("duration",0))/10_000_000
            w=str(chunk.get("text","")).strip()
            if w:
                raw.append({"text":w,"start":st,"raw_end":st+dur})
    if not audio_bytes:
        raise RuntimeError("TTS sem audio")
    with audio_path.open("wb") as f:
        f.write(audio_bytes)
    ad=probe(audio_path)
    if not raw:
        clean=text.split(); tpw=ad/max(1,len(clean))
        return [{"text":w,"start":i*tpw,"end":(i+1)*tpw} for i,w in enumerate(clean)], ad
    last_raw=max(w["raw_end"] for w in raw)
    # SYNC ZERO: termina exatamente em ad
    scale=ad/max(0.1, last_raw)
    words=[]
    for w in raw:
        s=w["start"]*scale
        e=w["raw_end"]*scale
        if e-s<0.26:
            e=s+0.26
        words.append({"text":w["text"],"start":s,"end":e})
    return words, ad

def render(source, audio, headline, caps, words, out, dur):
    CAPTION_Y = int(H*0.68)
    filters=[f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setpts=N/FRAME_RATE/TB[bg]"]
    last="[bg]"; idx=0
    filters.append(f"{last}[2:v]overlay=0:12[tmp{idx}]"); last=f"[tmp{idx}]"; idx+=1
    for i,w in enumerate(words):
        s=w["start"]; e=min(dur, w["end"])
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
    return HTMLResponse("<h1>V176 - 3 PILULAS COLORIDAS + SYNC ZERO</h1><a href='/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA'>GERAR V176</a>")

@app.get("/health")
def health():
    return {"status":"ok","version":VERSION}

@app.get("/render-web")
async def render_web(video_url: str = Query("https://www.tiktok.com/@carey_collections/video/7688751450901597461"), headline: str = Query("ACHADINHO QUE FACILITA SUA VIDA")):
    clean()
    job=uuid.uuid4().hex; folder=JOBS/job; folder.mkdir(parents=True)
    caps_dir=folder/"caps"; caps_dir.mkdir()
    try:
        src=download(video_url, folder)
        audio=folder/"narr.mp3"
        txt="Olha esse achadinho incrivel para sua casa! Pratico, moderno e vai facilitar demais a sua rotina. Corre no link da bio e garanta o seu antes que esgote!"
        tmp=folder/"tmp.mp3"
        words, ad = await get_words_sync_zero(txt, tmp)
        import shutil
        shutil.copy(tmp, audio)
        # ZERO ATRASO: dur = last end, sem +0.12
        dur = max(w["end"] for w in words) + 0.05
        caps=[]
        for i,w in enumerate(words):
            p=caps_dir/f"cap_{i:03d}.png"
            make_ransom_word(p, w["text"], fsize=72, canvas_h=600)
            caps.append(p)
        hl=folder/"head.png"
        make_headline_ransom_3_pills(hl, headline)
        out=folder/"final.mp4"
        render(src, audio, hl, caps, words, out, dur)
        return FileResponse(out, media_type="video/mp4", filename="klebee_v176.mp4")
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(500, f"Erro: {e}")

if __name__=="__main__":
    import uvicorn
    port=int(os.environ.get("PORT",8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
