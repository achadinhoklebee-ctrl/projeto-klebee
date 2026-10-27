"""Super Robô Klebee — V169 - FIX THREADS 60 -> 2 - DEFINITIVO - NAO DA MAIS -9"""
from __future__ import annotations
import os, shutil, subprocess, uuid, traceback, time
from pathlib import Path
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-V169-THREADS-FIX"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920
VOICE = "pt-BR-FranciscaNeural"
RATE = "+10%"
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
        # Mostra só últimas 2000 chars pra não quebrar JSON
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

def make_headline_print4(path: Path, text: str):
    img = Image.new("RGBA", (W, 650), (0,0,0,0))
    d = ImageDraw.Draw(img)
    f = font(135)
    words = text.upper().split()
    lines, cur = [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        bb = d.textbbox((0,0), cand, font=f, stroke_width=18)
        if bb[2]-bb[0] <= W-80:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    lines = lines[:3]
    y = 15
    for line in lines:
        bb = d.textbbox((0,0), line, font=f, stroke_width=18)
        x = (W - (bb[2]-bb[0])) // 2
        d.text((x+5,y+5), line, font=f, fill="black", stroke_width=18, stroke_fill="black")
        d.text((x,y), line, font=f, fill="#FFE500", stroke_width=18, stroke_fill="black")
        y += bb[3]-bb[1]+20
    img.save(path)

def ass_time(s: float) -> str:
    n = max(0, round(s*100))
    h,n = divmod(n,360000); m,n = divmod(n,6000); sec,cs = divmod(n,100)
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

def esc(s: str) -> str:
    return s.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")

def make_ass_70pct(path: Path, words, duration: float):
    header = """[Script Info]
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: C,DejaVu Sans,96,&H0000E5FF,&H0000E5FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,12,2,2,80,80,615,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for w in words:
        s = w["start"]; e = min(duration, w["end"])
        if e <= s:
            e = s+0.4
        ev.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},C,,0,0,0,,{esc(w['text'])}")
    path.write_text(header + "\n".join(ev) + "\n", encoding="utf-8")

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
        return 10.0

def render_definitivo(source, audio, headline, ass_p, out, dur):
    # FIX THREADS 60 -> 2 - IGUAL V157 QUE FUNCIONAVA
    ass_path = str(ass_p.resolve()).replace(":", "\\:").replace("'", "")
    cmd = [
        binary("ffmpeg"),"-y",
        "-threads","2",
        "-stream_loop","1","-i",str(source),
        "-i",str(audio),
        "-i",str(headline),
        "-filter_complex",
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setpts=N/FRAME_RATE/TB[bg];[bg][2:v]overlay=0:30[hd];[hd]ass='{ass_path}'[v];[1:a]volume=1.25[av];[0:a]volume=0.15[am];[av][am]amix=inputs=2:duration=first:dropout_transition=0[a]",
        "-map","[v]","-map","[a]",
        "-t",f"{dur:.2f}",
        "-threads","2",
        "-c:v","libx264","-preset","ultrafast","-crf","26","-x264-params","threads=2",
        "-c:a","aac","-b:a","128k",
        str(out)
    ]
    run(cmd,400)

def clean():
    try:
        for d in JOBS.glob("*"):
            if d.is_dir() and time.time()-d.stat().st_mtime>900:
                shutil.rmtree(d, ignore_errors=True)
    except:
        pass

@app.get("/")
def home():
    return HTMLResponse("<h1>V169 - FIX THREADS - DEFINITIVO</h1><a href='/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA'>GERAR V169</a>")

@app.get("/health")
def health():
    return {"status":"ok","version":VERSION}

@app.get("/render-web")
async def render_web(video_url: str = Query("https://www.tiktok.com/@carey_collections/video/7688751450901597461"), headline: str = Query("ACHADINHO INCRIVEL!")):
    clean()
    job = uuid.uuid4().hex; folder = JOBS/job; folder.mkdir(parents=True)
    try:
        src = download(video_url, folder)
        audio = folder/"narr.mp3"
        txt = "Olha esse achadinho incrivel para sua casa! Pratico, moderno e vai facilitar demais a sua rotina. Corre no link da bio e garanta o seu antes que esgote!"
        tmp = folder/"tmp.mp3"
        comm = edge_tts.Communicate(txt, VOICE, rate=RATE)
        data = bytearray()
        async for c in comm.stream():
            if c["type"]=="audio":
                data.extend(c["data"])
        tmp.write_bytes(data)
        ad = probe(tmp)
        dur = min(16.0, max(10.5, ad+0.3))
        usable = max(0.5, ad-0.35)
        words_txt = txt.split()
        tpw = usable / len(words_txt)
        comm2 = edge_tts.Communicate(txt, VOICE, rate=RATE)
        data2 = bytearray()
        async for c in comm2.stream():
            if c["type"]=="audio":
                data2.extend(c["data"])
        audio.write_bytes(data2)
        words = []
        for i, w in enumerate(words_txt):
            s = 0.15 + i*tpw
            words.append({"text": w, "start": s, "end": s+tpw})
        ass = folder/"cap.ass"
        make_ass_70pct(ass, words, dur)
        hl = folder/"head.png"
        make_headline_print4(hl, headline)
        out = folder/"final.mp4"
        render_definitivo(src, audio, hl, ass, out, dur)
        return FileResponse(out, media_type="video/mp4", filename="klebee_v169.mp4")
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(500, f"Erro: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
