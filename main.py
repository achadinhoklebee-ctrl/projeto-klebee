"""Super Robô Klebee — V154 - FIX CORTE DE TEXTO - 2 PALAVRAS POR VEZ"""
from __future__ import annotations
import os, shutil, subprocess, uuid, traceback
from pathlib import Path
from typing import Any
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "KLEBEE-V154-NO-CUT"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1080, 1920, 30
VOICE = os.getenv("KLEBEE_TTS_VOICE", "pt-BR-AntonioNeural")
RATE = os.getenv("KLEBEE_TTS_RATE", "+15%")
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
    image = Image.new("RGBA", (W, 480), (0,0,0,0))
    draw = ImageDraw.Draw(image)
    size = 110
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

def ass_time(s: float) -> str:
    n = max(0, round(s*100))
    h,n = divmod(n,360000); m,n = divmod(n,6000); sec,cs = divmod(n,100)
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

def esc_ass(s: str) -> str:
    return s.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")

async def make_voice(text: str, path: Path):
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    audio_bytes = bytearray(); words=[]
    async for chunk in comm.stream():
        if chunk["type"] == "audio": audio_bytes.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            st = float(chunk.get("offset",0))/10_000_000
            dur = float(chunk.get("duration",0))/10_000_000
            w = str(chunk.get("text","")).strip()
            if w: words.append({"text":w, "start":st, "end":st+dur})
    if not audio_bytes: raise RuntimeError("TTS sem audio")
    with path.open("wb") as f: f.write(audio_bytes)
    if not words:
        clean=text.split(); dur=max(3.0, len(audio_bytes)/16000.0); step=dur/max(1,len(clean))
        words=[{"text":w,"start":i*step,"end":(i+1)*step} for i,w in enumerate(clean)]
    return words

def make_ass_fix_corte(path: Path, words, duration: float):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,8,2,2,80,80,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    blocks=[]
    cur=[]
    for w in words:
        cur.append(w)
        # FIX: maximo 2 palavras por bloco (padrao TikTok viral)
        if len(cur)>=2 or w["text"].endswith((".", "!", "?", ",")):
            blocks.append(cur)
            cur=[]
    if cur: blocks.append(cur)

    events=[]
    last_end=0.0
    for block in blocks:
        for idx, active in enumerate(block):
            s = max(active["start"], last_end + 0.01)
            if idx+1 < len(block):
                e = block[idx+1]["start"] - 0.01
            else:
                # Ultima palavra segura ate proximo bloco
                next_block_start = None
                try:
                    b_idx = blocks.index(block)
                    if b_idx+1 < len(blocks):
                        next_block_start = blocks[b_idx+1][0]["start"]
                except: pass
                if next_block_start:
                    e = next_block_start - 0.01
                else:
                    e = min(duration, active["end"]+0.45)
            if e <= s: e = s + 0.30

            parts=[]
            for j, bw in enumerate(block):
                tok=esc_ass(bw["text"])
                if j==idx:
                    parts.append(f"{{\\c&H00E5FF&\\b1}}{tok}{{\\c&HFFFFFF&\\b0}}")
                else:
                    parts.append(tok)
            line=" ".join(parts)
            events.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Caption,,0,0,0,,{line}")
            last_end=e

    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")

def download(url: str, folder: Path) -> Path:
    opts={"format":"bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best","outtmpl":str(folder/"source.%(ext)s"),"noplaylist":True,"quiet":True,"no_warnings":True,"merge_output_format":"mp4","retries":2,"socket_timeout":25}
    with YoutubeDL(opts) as ydl: ydl.extract_info(url, download=True)
    cands=[p for p in folder.glob("source.*") if p.is_file() and p.stat().st_size>100_000]
    if not cands: raise RuntimeError("Sem video")
    return max(cands, key=lambda p: p.stat().st_size)

def probe_duration(path: Path) -> float:
    p=run([binary("ffprobe"),"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],60)
    return float(p.stdout.strip())

def render(source, audio, ass, headline, output, duration):
    ass_path=str(ass.resolve()).replace("\\","/").replace(":","\\:").replace("'","\\'")
    hl_path=str(headline.resolve()).replace("\\","/")
    cmd=[binary("ffmpeg"),"-y","-i",str(source),"-i",str(audio),"-i",hl_path,"-filter_complex",f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}[bg];[bg][2:v]overlay=0:45[with_headline];[with_headline]ass='{ass_path}'[v];[0:a]volume=0.20[a_music];[1:a]volume=1.15[a_voice];[a_music][a_voice]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[a_final]","-map","[v]","-map","[a_final]","-t",f"{duration:.3f}","-threads","4","-c:v","libx264","-preset","ultrafast","-crf","20","-c:a","aac","-b:a","192k","-shortest",str(output)]
    run(cmd,400)

@app.get("/")
def home(): return HTMLResponse(f"<h1>KLEBEE V154 - FIX CORTE</h1><a href='/render-web?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461&headline=ACHADINHO%20QUE%20FACILITA%20SUA%20VIDA'>GERAR V154</a>")

@app.get("/health")
def health(): return {"status":"ok","version":VERSION}

@app.get("/render-web")
async def render_web(video_url: str = Query("https://www.tiktok.com/@carey_collections/video/7688751450901597461"), headline: str = Query("ACHADINHO INCRIVEL!")):
    job=uuid.uuid4().hex; folder=JOBS/job; folder.mkdir(parents=True)
    try:
        source=download(video_url,folder); audio=folder/"narration.mp3"
        txt="Olha esse achadinho incrivel para sua casa! Pratico, moderno e vai facilitar demais a sua rotina. Corre no link da bio e garanta o seu antes que esgote!"
        words=await make_voice(txt,audio); dur=min(16.0,max(10.0,probe_duration(audio)+0.2))
        ass=folder/"captions.ass"; make_ass_fix_corte(ass,words,dur)
        hl=folder/"headline.png"; make_headline(hl,headline)
        out=folder/"klebee.mp4"; render(source,audio,ass,hl,out,dur)
        return FileResponse(out, media_type="video/mp4", filename="klebee_v154.mp4")
    except Exception as e:
        print(traceback.format_exc()); raise HTTPException(500,f"Erro: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
