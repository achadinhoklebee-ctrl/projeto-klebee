from __future__ import annotations
import os, shutil, subprocess, uuid, traceback, random
from pathlib import Path
import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "V180-FIX-BORRAO-UTENSILIOS-SYNC"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920
VOICE = "pt-BR-FranciscaNeural"
RATE = "+10%"
CAPTION_Y = int(H * 0.58)
HEADLINE_Y = 12

PALETTE = [("#FFEB3B","black"),("#FF6B00","white"),("#FFFFFF","black"),("#000000","white"),("#03A9F4","white"),("#E91E63","white")]
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

app = FastAPI(title="V180", version=VERSION)

def fix_pronuncia_utensilios(text):
    if not text:
        return text
    reps = {
        "utensilios": "utensílios",
        "UTENSILIOS": "UTENSÍLIOS",
        "Utensilios": "Utensílios",
        "organizador de utensilios": "organizador de utensílios",
        "porta utensilios": "porta utensílios"
    }
    for w,c in reps.items():
        text = text.replace(w,c)
    return text

def apply_zero_sync_fix_V180(words, audio_dur):
    if not words:
        return words, audio_dur
    real = max(0.5, audio_dur - 0.25)
    last = len(words)-1
    if last >= 0:
        words[last]['end'] = real - 0.05
        if last >= 1:
            words[last]['start'] = words[last-1]['end']
            if words[last]['start'] >= words[last]['end']:
                words[last]['start'] = words[last]['end'] - 0.3
    return words, real

def binary(n: str):
    import shutil
    p=shutil.which(n)
    if not p: raise RuntimeError(n)
    return p

def run(args, timeout=600):
    import subprocess
    p=subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-3000:])
    return p

def font(sz):
    for fp in FONTS:
        if Path(fp).is_file():
            try:
                return ImageFont.truetype(fp, size=sz)
            except:
                pass
    return ImageFont.load_default()

def make_ransom_word(path: Path, word: str, fsize=72, canvas_h=600, canvas_w=1080):
    MAX_W = canvas_w - 100
    cur_fsize = fsize
    final_ws = []
    final_total = 0
    for _ in range(8):
        f = font(cur_fsize)
        dummy = ImageDraw.Draw(Image.new("RGBA",(1,1)))
        ws = []
        total = 0
        for lt in word.upper():
            if lt.strip() == "":
                ws.append(40)
                total += 40
            else:
                try:
                    bb = dummy.textbbox((0,0), lt, font=f)
                    w = bb[2]-bb[0]
                except:
                    w = cur_fsize*0.6
                ws.append(w)
                total += w + 16
        if total <= MAX_W or cur_fsize <= 38:
            final_ws = ws
            final_total = total
            break
        scale = MAX_W / total
        cur_fsize = max(38, int(cur_fsize * scale * 0.92))
    f = font(cur_fsize)
    tmp_img = Image.new("RGBA", (canvas_w, canvas_h), (0,0,0,0))
    x = (canvas_w - final_total)//2
    y_center = canvas_h//2
    for i, lt in enumerate(word.upper()):
        if lt.strip() == "":
            x += 40
            continue
        bg, txt = random.choice(PALETTE)
        lw = int(final_ws[i] + 22)
        lh = int(cur_fsize * 1.2) + 12
        li = Image.new("RGBA", (lw, lh), (0,0,0,0))
        ImageDraw.Draw(li).rectangle([0,0,lw,lh], fill=bg)
        try:
            bb = ImageDraw.Draw(Image.new("RGBA",(1,1))).textbbox((0,0), lt, font=f)
            tw = bb[2]-bb[0]
            th = bb[3]-bb[1]
        except:
            tw = cur_fsize*0.6
            th = cur_fsize
        tx = (lw - tw)//2
        ty = (lh - th)//2 - 2
        ImageDraw.Draw(li).text((tx, ty), lt, font=f, fill=txt)
        rot = li.rotate(random.uniform(-4,4), resample=Image.BICUBIC, expand=True)
        y_off = y_center - rot.height//2 + random.randint(-3,3)
        y_off = max(10, min(y_off, canvas_h - rot.height - 10))
        tmp_img.alpha_composite(rot, (int(x), int(y_off)))
        x += lw - 6
    bbox = tmp_img.getbbox()
    if bbox:
        cropped = tmp_img.crop(bbox)
        final = Image.new("RGBA", (canvas_w, canvas_h), (0,0,0,0))
        fx = (canvas_w - cropped.width)//2
        fy = (canvas_h - cropped.height)//2
        final.alpha_composite(cropped, (fx, fy))
        final.save(path)
    else:
        tmp_img.save(path)

def make_headline_2lines(path: Path, text: str):
    text = fix_pronuncia_utensilios(text)
    img = Image.new("RGBA", (W, 420), (0,0,0,0))
    parts = text.upper().split()
    if len(parts) <= 2:
        l1 = parts[0] if parts else "ACHADINHO"
        l2 = " ".join(parts[1:]) if len(parts)>1 else "INCRIVEL"
    else:
        mid = len(parts)//2
        l1 = " ".join(parts[:mid])
        l2 = " ".join(parts[mid:])
    lines = [l1, l2]
    pill_colors = ["#FFEB3B", "#FF6B00"]
    y = 12
    for idx, line in enumerate(lines):
        fsize = 88
        if len(line) > 18: fsize = 72
        if len(line) > 26: fsize = 58
        tmp = path.parent / f"hl_{idx}_{uuid.uuid4().hex[:3]}.png"
        make_ransom_word(tmp, line, fsize=fsize, canvas_h=200, canvas_w=W)
        try:
            li = Image.open(tmp)
        except:
            continue
        bbox = li.getbbox()
        crop = li.crop(bbox) if bbox else li
        pw = crop.width + 70
        ph = crop.height + 36
        if pw > W - 20: pw = W - 20
        pill = Image.new("RGBA", (pw, ph), (0,0,0,0))
        pd = ImageDraw.Draw(pill)
        pd.rounded_rectangle([6,8,pw-2,ph-4], radius=18, fill=(0,0,0,200))
        pd.rounded_rectangle([0,0,pw-8,ph-10], radius=18, fill=pill_colors[idx])
        px = (pw - crop.width)//2
        py = (ph - crop.height)//2 - 2
        pill.alpha_composite(crop, (px, py))
        rot = pill.rotate([-2.2, 1.9][idx], resample=Image.BICUBIC, expand=True)
        img.alpha_composite(rot, ((W-rot.width)//2, y))
        y += rot.height - 4
        try: tmp.unlink()
        except: pass
    img.save(path)

def make_caps_video(caps, words, out, dur):
    fps = 10
    total_frames = int(dur * fps) + 2
    frames_dir = out.parent / "caps_frames"
    frames_dir.mkdir(exist_ok=True)
    for f_idx in range(total_frames):
        t = f_idx / fps
        active = None
        for i,w in enumerate(words):
            if w["start"] <= t <= w["end"]:
                active = i
                break
        frame_path = frames_dir / f"f_{f_idx:04d}.png"
        if active is not None:
            shutil.copy(caps[active], frame_path)
        else:
            Image.new("RGBA",(W,600),(0,0,0,0)).save(frame_path)
    run([binary("ffmpeg"),"-y","-framerate",str(fps),"-i",str(frames_dir/"f_%04d.png"),"-c:v","png","-pix_fmt","rgba","-t",f"{dur:.2f}",str(out)],600)
    shutil.rmtree(frames_dir, ignore_errors=True)

async def get_words(text, audio_path):
    text = fix_pronuncia_utensilios(text)
    comm=edge_tts.Communicate(text, VOICE, rate=RATE)
    audio_bytes=bytearray(); raw=[]
    async for chunk in comm.stream():
        if chunk["type"]=="audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"]=="WordBoundary":
            st=float(chunk.get("offset",0))/10_000_000
            dur=float(chunk.get("duration",0))/10_000_000
            w=str(chunk.get("text","")).strip()
            if w: raw.append({"text":w,"start":st,"raw_end":st+dur})
    if not audio_bytes:
        raise RuntimeError("TTS sem audio")
    with audio_path.open("wb") as f:
        f.write(audio_bytes)
    def probe(p):
        r=run([binary("ffprobe"),"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(p)],60)
        try: return float(r.stdout.strip())
        except: return 10.0
    ad=probe(audio_path)
    if not raw:
        clean=text.split(); tpw=ad/max(1,len(clean))
        return [{"text":w,"start":i*tpw,"end":(i+1)*tpw} for i,w in enumerate(clean)], ad
    last_raw=max(w["raw_end"] for w in raw)
    scale=ad/max(0.1,last_raw)
    words=[{"text":w["text"],"start":w["start"]*scale,"end":w["raw_end"]*scale} for w in raw]
    for w in words:
        if w["end"]-w["start"]<0.28: w["end"]=w["start"]+0.28
    # V180 ZERO SYNC
    words, ad = apply_zero_sync_fix_V180(words, ad)
    return words, ad

def download(url, folder):
    opts={"format":"bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best","outtmpl":str(folder/"source.%(ext)s"),"noplaylist":True,"quiet":True,"no_warnings":True,"merge_output_format":"mp4"}
    with YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
    cands=[p for p in folder.glob("source.*") if p.is_file() and p.stat().st_size>50000]
    if not cands: raise RuntimeError("Sem video")
    return max(cands, key=lambda p:p.stat().st_size)

def render_final_fix(source, audio, headline, caps_video, watermark, out, dur):
    filters=[
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setpts=N/FRAME_RATE/TB[bg]",
        f"[bg][2:v]overlay=0:{HEADLINE_Y}[tmp0]",
        f"[tmp0][3:v]overlay=(W-w)/2:{CAPTION_Y}[tmp1]",
        f"[tmp1][4:v]overlay=W-w-20:450:format=rgb:alpha=1[final]",
        "[1:a]volume=1.25[av];[0:a]volume=0.15[am];[av][am]amix=inputs=2:duration=first:dropout_transition=0[a]"
    ]
    fc=";".join(filters)
    cmd=[binary("ffmpeg"),"-y","-threads","2","-stream_loop","1","-i",str(source),"-i",str(audio),"-i",str(headline),"-i",str(caps_video),"-i",str(watermark),
         "-filter_complex",fc,"-map","[final]","-map","[a]","-t",f"{dur:.2f}","-threads","2","-c:v","libx264","-preset","ultrafast","-crf","26","-c:a","aac","-b:a","128k",str(out)]
    run(cmd,600)

@app.get("/", response_class=HTMLResponse)
def home():
    return f"<h1>{VERSION}</h1><p>V180 FIX BORRAO + UTENSILIOS + SYNC | 2 linhas | 58% | watermark nitido | utensilios com acento | sync 11s=11s</p><a href='/render'><h2>GERAR VIDEO</h2></a>"

@app.get("/health")
def health():
    return {"version":VERSION}

@app.get("/render")
async def render():
    job=uuid.uuid4().hex; folder=JOBS/job; folder.mkdir(parents=True); caps_dir=folder/"caps"; caps_dir.mkdir()
    try:
        src=download("https://www.tiktok.com/@carey_collections/video/7688751450901597461", folder)
        roteiro="Olha esse organizador de gaveta que vai transformar sua cozinha! Bambu natural, cinco compartimentos, resistente e elegante. Organiza talheres, utensílios e deixa tudo no lugar. Corre no link e garanta o seu!"
        roteiro = fix_pronuncia_utensilios(roteiro)
        headline_text=fix_pronuncia_utensilios("ACHADINHO QUE ORGANIZA")
        audio_tmp=folder/"tmp.mp3"; audio_final=folder/"narr.mp3"
        words, ad = await get_words(roteiro, audio_tmp)
        import shutil; shutil.copy(audio_tmp, audio_final)
        dur=max(w["end"] for w in words)+0.05
        caps=[]
        for i,w in enumerate(words):
            p=caps_dir/f"cap_{i:03d}.png"
            make_ransom_word(p,w["text"],fsize=72,canvas_h=600,canvas_w=W)
            caps.append(p)
        caps_video=folder/"caps_video.mov"
        make_caps_video(caps, words, caps_video, dur)
        hl=folder/"headline.png"
        make_headline_2lines(hl, headline_text)
        wm_src = Path(__file__).parent / "assets" / "klebee_watermark_180_final.png"
        wm_dst = folder / "watermark.png"
        if wm_src.exists():
            shutil.copy(wm_src, wm_dst)
        else:
            Image.new("RGBA",(180,180),(255,107,0,200)).save(wm_dst)
        out=folder/"final_v180.mp4"
        render_final_fix(src, audio_final, hl, caps_video, wm_dst, out, dur)
        return FileResponse(out, media_type="video/mp4", filename="klebee_v180_fix.mp4")
    except Exception as e:
        import traceback; print(traceback.format_exc())
        raise HTTPException(500, f"Erro: {e}")

if __name__=="__main__":
    import uvicorn, os
    port=int(os.getenv("PORT","8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
