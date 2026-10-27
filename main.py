"""
KLEBEE VIDEO-AUTORAL V177 - 2 LINHAS + LEGENDA 58% (ACIMA LINK SHOPEE)
Base: V176 aprovado pelo usuario - sem OOM, sem SyntaxError
Correcoes V177:
1. Headline sempre 2 linhas (antes 3) - novo texto que cabe em 2 linhas
2. Caption Y = H*0.58 (antes 0.68) - sobe 192px pra ficar acima do card Shopee
   Foto 2 do usuario: card "Porta Talheres R$39,90 Comprar com cupom" comeca em 70%
NUNCA citar valores no video
"""
from __future__ import annotations
import os, shutil, subprocess, uuid, traceback, time, random
from pathlib import Path
import edge_tts
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from yt_dlp import YoutubeDL

VERSION = "V177-2LINHAS-LEGENDA58"
ROOT = Path(os.getenv("KLEBEE_WORKDIR", "/tmp/klebee"))
JOBS = ROOT / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920
VOICE = "pt-BR-FranciscaNeural"
RATE = "+10%"
# CAPTION_Y CORRIGIDO - 58% pra ficar acima do link Shopee (foto 2)
CAPTION_Y = int(H * 0.58)  # 1113px - antes 1305px (68%) - sobe 192px
# HEADLINE_Y continua topo
HEADLINE_Y = 15

PALETTE = [
    ("#FFEB3B", "black"),
    ("#FF6B00", "white"),
    ("#FFFFFF", "black"),
    ("#000000", "white"),
    ("#03A9F4", "white"),
    ("#E91E63", "white"),
    ("#4CAF50", "white"),
]

FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

app = FastAPI(title="Klebee Video Autoral V177", version=VERSION)

def binary(n: str):
    p = shutil.which(n)
    if not p:
        raise RuntimeError(f"Sem binario {n}")
    return p

def run(args, timeout=500):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"FFmpeg/FFprobe erro {p.returncode}: {(p.stderr or p.stdout)[-2000:]}")
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
    ws = []
    total = 0
    dummy = ImageDraw.Draw(Image.new("RGBA", (1,1)))
    for lt in letters:
        if lt.strip() == "":
            ws.append(14)
            total += 14
        else:
            try:
                bb = dummy.textbbox((0,0), lt, font=f)
                w = bb[2]-bb[0]
            except:
                w = fsize*0.7
            ws.append(w)
            total += w + 6
    x = (W - total)//2
    y_center = canvas_h//2
    for i, lt in enumerate(letters):
        if lt.strip() == "":
            x += 14
            continue
        bg, txt = random.choice(PALETTE)
        lw = int(ws[i] + 22)
        lh = 88
        li = Image.new("RGBA", (lw, lh), (0,0,0,0))
        ImageDraw.Draw(li).rectangle([0,0,lw,lh], fill=bg)
        ImageDraw.Draw(li).text((11,10), lt, font=f, fill=txt)
        rot = li.rotate(random.uniform(-6,6), resample=Image.BICUBIC, expand=True)
        y_off = max(5, min(y_center - rot.height//2 + random.randint(-5,5), canvas_h - rot.height - 5))
        img.alpha_composite(rot, (int(x), int(y_off)))
        x += lw - 6
    img.save(path)

def make_headline_2lines(path: Path, text: str):
    """
    V177 - Headline sempre 2 linhas (antes 3)
    Texto novo para teste que cabe em 2 linhas: ex "ACHADINHO QUE ORGANIZA"
    -> Linha1: ACHADINHO QUE
    -> Linha2: ORGANIZA (ou similar)
    Sem valores, sem preco
    """
    img = Image.new("RGBA", (W, 420), (0,0,0,0))
    # Forca 2 linhas
    parts = text.upper().split()
    if len(parts) == 2:
        l1, l2 = parts[0], parts[1]
    elif len(parts) == 3:
        l1 = " ".join(parts[:1])
        l2 = " ".join(parts[1:])
    elif len(parts) >= 4:
        mid = len(parts)//2
        l1 = " ".join(parts[:mid])
        l2 = " ".join(parts[mid:])
    else:
        l1 = text.upper()
        l2 = "INCRIVEL"
    lines = [l1, l2]
    pill_colors = ["#FFEB3B", "#FF6B00"]  # amarelo e laranja - 2 linhas
    y = 15
    for idx, line in enumerate(lines):
        # Evita texto muito longo cortando - reduz fonte se precisar
        fsize = 88
        if len(line) > 18:
            fsize = 72
        if len(line) > 25:
            fsize = 60
        tmp = path.parent / f"hl_tmp_{idx}_{uuid.uuid4().hex[:4]}.png"
        make_ransom_word(tmp, line, fsize=fsize, canvas_h=170)
        try:
            line_img = Image.open(tmp)
        except:
            continue
        bbox = line_img.getbbox()
        cropped = line_img.crop(bbox) if bbox else line_img
        pill_w = cropped.width + 60
        pill_h = cropped.height + 24
        # Limita largura pra nao estourar 1080
        if pill_w > W - 20:
            pill_w = W - 20
        pill = Image.new("RGBA", (pill_w, pill_h), (0,0,0,0))
        pd = ImageDraw.Draw(pill)
        pd.rounded_rectangle([5,7,pill_w-1,pill_h-3], radius=18, fill=(0,0,0,200))
        pd.rounded_rectangle([0,0,pill_w-6,pill_h-8], radius=18, fill=pill_colors[idx])
        # centraliza cropped dentro da pilula
        cx = (pill_w - cropped.width)//2
        cy = (pill_h - cropped.height)//2 - 4
        pill.alpha_composite(cropped, (cx, cy))
        rot = pill.rotate([-2.2, 1.9][idx], resample=Image.BICUBIC, expand=True)
        img.alpha_composite(rot, ((W-rot.width)//2, y))
        y += rot.height - 8
        try:
            tmp.unlink()
        except:
            pass
    img.save(path)

async def get_words_and_audio(text: str, audio_path: Path):
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    audio_bytes = bytearray()
    raw = []
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            st = float(chunk.get("offset",0))/10_000_000
            dur = float(chunk.get("duration",0))/10_000_000
            w = str(chunk.get("text","")).strip()
            if w:
                raw.append({"text": w, "start": st, "raw_end": st+dur})
    if not audio_bytes:
        raise RuntimeError("TTS sem audio")
    with audio_path.open("wb") as f:
        f.write(audio_bytes)

    def probe(p: Path):
        r = run([binary("ffprobe"),"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(p)],60)
        try:
            return float(r.stdout.strip())
        except:
            return 10.0
    ad = probe(audio_path)
    if not raw:
        clean = text.split()
        tpw = ad / max(1,len(clean))
        words = [{"text": w, "start": i*tpw, "end": (i+1)*tpw} for i,w in enumerate(clean)]
        return words, ad
    last_raw = max(w["raw_end"] for w in raw)
    scale = ad / max(0.1, last_raw)
    words = [{"text": w["text"], "start": w["start"]*scale, "end": w["raw_end"]*scale} for w in raw]
    for w in words:
        if w["end"]-w["start"] < 0.28:
            w["end"] = w["start"] + 0.28
    return words, ad

def download_source(url: str, out: Path):
    ydl_opts = {
        "outtmpl": str(out),
        "format": "mp4/best",
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def render_final(source: Path, audio: Path, headline: Path, caps: list[Path], words: list[dict], out: Path, dur: float):
    filters = [
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setpts=N/FRAME_RATE/TB[bg]"
    ]
    last = "[bg]"
    idx = 0
    # Headline
    filters.append(f"{last}[2:v]overlay=0:{HEADLINE_Y}[tmp{idx}]")
    last = f"[tmp{idx}]"
    idx += 1
    # Captions - nova posicao 58% (acima do link Shopee)
    for i, w in enumerate(words):
        s = w["start"]
        e = min(dur, w["end"])
        filters.append(f"{last}[{3+i}:v]overlay=(W-w)/2:{CAPTION_Y}:enable='between(t,{s:.3f},{e:.3f})'[tmp{idx}]")
        last = f"[tmp{idx}]"
        idx += 1
    # Audio ducking
    filters.append("[1:a]volume=1.25[av];[0:a]volume=0.15[am];[av][am]amix=inputs=2:duration=first:dropout_transition=0[a]")
    fc = ";".join(filters)
    cmd = [binary("ffmpeg"),"-y","-threads","2","-stream_loop","1","-i",str(source),"-i",str(audio),"-i",str(headline)]
    for p in caps:
        cmd.extend(["-i",str(p)])
    cmd.extend(["-filter_complex",fc,"-map",last,"-map","[a]","-t",f"{dur:.2f}","-threads","2","-c:v","libx264","-preset","ultrafast","-crf","26","-c:a","aac","-b:a","128k",str(out)])
    run(cmd, 500)

# Roteiros sem valores
ROTEIROS = {
    "organizador": "Olha esse organizador de gaveta que vai transformar sua cozinha! Bambu natural, cinco compartimentos, resistente e elegante. Organiza talheres, utensilios e deixa tudo no lugar. Corre no link e garanta o seu!",
    "parafusadeira": "Olha essa parafusadeira profissional que vai facilitar sua vida! Quarenta e oito volts, com duas baterias, maleta e acessorios completos. Profissional, recarregavel, pronta pra qualquer reparo em casa. Corre no link da bio e garanta a sua!",
}

# Headlines 2 linhas - sem valores - novas para teste
HEADLINES_2L = {
    "organizador": "ACHADINHO QUE ORGANIZA",
    "parafusadeira": "ACHADINHO QUE FACILITA",
    "generica": "ACHADINHO QUE FACILITA SUA VIDA",
}

@app.get("/", response_class=HTMLResponse)
def home():
    return f"""
    <h1>{VERSION}</h1>
    <p>Headline 2 linhas | Caption {CAPTION_Y}px (58% - acima link Shopee)</p>
    <ul>
      <li><a href='/render?produto=organizador'>GERAR - Organizador (ACHADINHO QUE ORGANIZA)</a></li>
      <li><a href='/render?produto=parafusadeira'>GERAR - Parafusadeira (ACHADINHO QUE FACILITA)</a></li>
      <li><a href='/render?produto=generica'>GERAR - Generica 2 linhas</a></li>
    </ul>
    <p>V177 corrige foto 2 do usuario onde card Shopee cobria legenda</p>
    """

@app.get("/health")
def health():
    return {"status":"ok","version":VERSION,"caption_y":CAPTION_Y,"caption_percent":"58%","headline":"2 linhas"}

@app.get("/render")
async def render_video(
    produto: str = Query("organizador", description="organizador, parafusadeira, generica"),
    video_url: str = Query("", description="URL do video fonte (opcional)"),
):
    job = uuid.uuid4().hex
    folder = JOBS / job
    folder.mkdir(parents=True, exist_ok=True)
    caps_dir = folder / "caps"
    caps_dir.mkdir(exist_ok=True)
    try:
        # Escolhe roteiro e headline
        roteiro = ROTEIROS.get(produto, ROTEIROS["organizador"])
        headline_text = HEADLINES_2L.get(produto, HEADLINES_2L["organizador"])
        # Para generica que tem 4 palavras, forca 2 linhas: "ACHADINHO QUE" / "FACILITA SUA VIDA"
        if produto == "generica":
            headline_text = "ACHADINHO QUE ORGANIZA SUA COZINHA"

        # Source video
        source = folder / "source.mp4"
        if video_url:
            download_source(video_url, source)
        else:
            # fallback preto 15s
            run([binary("ffmpeg"),"-y","-f","lavfi","-i",f"color=c=0x222222:s={W}x{H}:d=15:r=30","-t","15",str(source)],60)

        audio_tmp = folder / "narr_tmp.mp3"
        audio_final = folder / "narr.mp3"
        words, ad = await get_words_and_audio(roteiro, audio_tmp)
        shutil.copy(audio_tmp, audio_final)

        # Duracao = ultimo word + 0.05 (V176 zero atraso aprovado)
        dur = max(w["end"] for w in words) + 0.05

        # Gera caps 1 palavra ransom 72pt
        caps = []
        for i, w in enumerate(words):
            p = caps_dir / f"cap_{i:03d}.png"
            make_ransom_word(p, w["text"], fsize=72, canvas_h=600)
            caps.append(p)

        # Gera headline 2 linhas
        hl = folder / "headline.png"
        make_headline_2lines(hl, headline_text)

        out = folder / "final_v177.mp4"
        render_final(source, audio_final, hl, caps, words, out, dur)

        return FileResponse(out, media_type="video/mp4", filename=f"klebee_v177_{produto}_2linhas_58.mp4")

    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        raise HTTPException(500, f"Erro V177: {e} | {tb[-1000:]}")
