import os
import re
import hashlib
import asyncio
import subprocess
from pathlib import Path

import edge_tts
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, ImageClip,
    CompositeAudioClip, concatenate_videoclips, concatenate_audioclips
)
from moviepy.audio.fx.all import volumex, audio_fadein, audio_fadeout

APP_VERSION = "KLEBEE-DYNAMIC-WORDS-2026-10-26-01"
app = FastAPI(title="Klebee Cloud Engine - Dynamic Captions", version=APP_VERSION)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "videos")
CACHE_AUDIO_DIR = os.path.join(BASE_DIR, "cache_audio")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_AUDIO_DIR, exist_ok=True)

WIDTH, HEIGHT = 1080, 1920
VOICE = "pt-BR-AntonioNeural"
VOICE_RATE = "+15%"
HEADLINE_Y = 170
CAPTION_Y = 1270
CAPTION_H = 300
SIDE_MARGIN = 90


def baixar_video_tiktok(url_tiktok: str) -> str:
    if not url_tiktok.startswith(("https://www.tiktok.com/", "https://vm.tiktok.com/",
                                  "https://vt.tiktok.com/")):
        raise ValueError("Informe uma URL HTTPS válida do TikTok.")
    key = hashlib.md5(url_tiktok.encode("utf-8")).hexdigest()
    output_path = os.path.join(CACHE_AUDIO_DIR, f"base_{key}.mp4")
    if os.path.exists(output_path) and os.path.getsize(output_path) > 100_000:
        return output_path
    temp_path = output_path + ".part"
    cmd = ["yt-dlp", "--no-playlist", "-f", "bv*+ba/b", "--merge-output-format", "mp4",
           "-o", temp_path, url_tiktok]
    subprocess.run(cmd, check=True, timeout=180)
    candidates = [temp_path, temp_path + ".mp4"]
    found = next((x for x in candidates if os.path.exists(x) and os.path.getsize(x) > 100_000), None)
    if not found:
        matches = sorted(Path(CACHE_AUDIO_DIR).glob(Path(temp_path).name + "*"),
                         key=lambda x: x.stat().st_mtime, reverse=True)
        found = str(matches[0]) if matches else None
    if not found:
        raise RuntimeError("O download terminou, mas o MP4 de origem não foi encontrado.")
    if found != output_path:
        os.replace(found, output_path)
    return output_path


async def gerar_audio_com_timestamps(texto: str):
    key = hashlib.sha256((texto + VOICE + VOICE_RATE).encode("utf-8")).hexdigest()
    audio_path = os.path.join(CACHE_AUDIO_DIR, f"voice_{key}.mp3")
    meta_path = os.path.join(CACHE_AUDIO_DIR, f"voice_{key}.words")
    words = []

    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 100 and os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                for line in f:
                    start, end, word = line.rstrip("\n").split("\t", 2)
                    words.append({"start": float(start), "end": float(end), "text": word})
            if words:
                return audio_path, words
        except Exception:
            words = []

    communicate = edge_tts.Communicate(texto, VOICE, rate=VOICE_RATE, boundary="WordBoundary")
    audio_bytes = bytearray()
    async for event in communicate.stream():
        if event["type"] == "audio":
            audio_bytes.extend(event["data"])
        elif event["type"] == "WordBoundary":
            start = float(event["offset"]) / 10_000_000
            duration = float(event["duration"]) / 10_000_000
            token = str(event["text"]).strip()
            if token:
                words.append({"start": max(0.0, start),
                              "end": max(start + 0.04, start + duration),
                              "text": token})
    if not audio_bytes:
        raise RuntimeError("O Edge TTS não retornou áudio.")
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)
    if words:
        with open(meta_path, "w", encoding="utf-8") as f:
            for w in words:
                f.write(f'{w["start"]:.6f}\t{w["end"]:.6f}\t{w["text"]}\n')
    else:
        raise RuntimeError("O Edge TTS não retornou eventos WordBoundary.")
    return audio_path, words


def carregar_fonte(tamanho: int):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, tamanho)
            except OSError:
                pass
    return ImageFont.load_default()


def limpar_texto_visual(texto: str) -> str:
    texto = re.sub(r"[\U0001F000-\U0001FAFF\U00002600-\U000027BF]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def medir(draw, texto, fonte):
    box = draw.textbbox((0, 0), texto, font=fonte, stroke_width=0)
    return box[2] - box[0], box[3] - box[1]


def quebrar_por_pixels(draw, palavras, fonte, max_width):
    linhas, atual = [], ""
    for palavra in palavras:
        teste = palavra if not atual else atual + " " + palavra
        largura, _ = medir(draw, teste, fonte)
        if largura <= max_width or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def criar_overlay_headline(texto: str, largura=WIDTH, altura=250) -> str:
    texto = limpar_texto_visual(texto)
    img = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    max_width = largura - 2 * SIDE_MARGIN
    font_size = 76
    while font_size >= 42:
        font = carregar_fonte(font_size)
        linhas = quebrar_por_pixels(draw, texto.split(), font, max_width)
        if len(linhas) <= 2 and all(medir(draw, line, font)[0] <= max_width for line in linhas):
            break
        font_size -= 2
    line_heights = [medir(draw, line, font)[1] for line in linhas]
    total_h = sum(line_heights) + max(0, len(linhas) - 1) * 7
    y = max(5, (altura - total_h) // 2)
    for linha, h in zip(linhas, line_heights):
        w, _ = medir(draw, linha, font)
        x = (largura - w) // 2
        draw.text((x, y), linha, font=font, fill="#FFE500",
                  stroke_width=5, stroke_fill="#111111")
        y += h + 7
    path = os.path.join(CACHE_AUDIO_DIR, "headline_" +
                        hashlib.md5(texto.encode("utf-8")).hexdigest() + ".png")
    img.save(path)
    return path


def criar_overlay_legenda_palavra(palavras_grupo, indice_ativo, largura=WIDTH,
                                    altura=CAPTION_H) -> str:
    palavras = [limpar_texto_visual(w) for w in palavras_grupo]
    palavras = [w for w in palavras if w]
    if not palavras:
        palavras = [" "]
    img = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    max_width = largura - 2 * SIDE_MARGIN - 42
    font_size = 54
    while font_size >= 34:
        font = carregar_fonte(font_size)
        linhas = []
        linha_indices = []
        current, current_idx = [], []
        for idx, palavra in enumerate(palavras):
            teste = " ".join(current + [palavra])
            if current and medir(draw, teste, font)[0] > max_width:
                linhas.append(current)
                linha_indices.append(current_idx)
                current, current_idx = [palavra], [idx]
            else:
                current.append(palavra)
                current_idx.append(idx)
        if current:
            linhas.append(current)
            linha_indices.append(current_idx)
        widths = [medir(draw, " ".join(line), font)[0] for line in linhas]
        heights = [medir(draw, " ".join(line), font)[1] for line in linhas]
        if max(widths, default=0) <= max_width and len(linhas) <= 3:
            break
        font_size -= 2

    pad_x, pad_y, gap = 28, 17, 9
    box_w = min(largura - 2 * SIDE_MARGIN, max(widths, default=100) + 2 * pad_x)
    box_h = sum(heights) + max(0, len(heights)-1) * gap + 2 * pad_y
    bx, by = (largura-box_w)//2, (altura-box_h)//2
    draw.rounded_rectangle((bx, by, bx+box_w, by+box_h), radius=18,
                           fill=(0, 0, 0, 185))
    y = by + pad_y
    for line, ids, h in zip(linhas, linha_indices, heights):
        widths_words = [medir(draw, word, font)[0] for word in line]
        spaces = medir(draw, " ", font)[0]
        line_w = sum(widths_words) + spaces * max(0, len(line)-1)
        x = (largura-line_w)//2
        for word, idx, ww in zip(line, ids, widths_words):
            color = "#FFE500" if idx == indice_ativo else "#FFFFFF"
            draw.text((x, y), word, font=font, fill=color,
                      stroke_width=2, stroke_fill="#111111")
            x += ww + spaces
        y += h + gap

    key = hashlib.md5(( "|".join(palavras) + f"_{indice_ativo}_{font_size}" ).encode("utf-8")).hexdigest()
    path = os.path.join(CACHE_AUDIO_DIR, f"caption_{key}.png")
    img.save(path)
    return path


def montar_clips_legenda(words, duracao):
    clips = []
    group_size = 4
    for group_start in range(0, len(words), group_size):
        group = words[group_start:group_start + group_size]
        for local_idx, word in enumerate(group):
            start = max(0.0, float(word["start"]))
            end = min(float(duracao), max(start + 0.06, float(word["end"])))
            if start >= duracao or end <= start:
                continue
            if local_idx + 1 < len(group):
                end = min(duracao, max(end, float(group[local_idx + 1]["start"])))
            path = criar_overlay_legenda_palavra(
                [w["text"] for w in group], local_idx
            )
            clips.append(
                ImageClip(path).set_start(start).set_duration(max(0.06, end-start))
                .set_pos(("center", CAPTION_Y))
            )
    return clips


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Super Robô Klebee - Cloud Engine V144 Pro</title>
        <style>
            body { background: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Arial, sans-serif; text-align: center; padding-top: 60px; }
            .card { background: #1e293b; padding: 40px; border-radius: 16px; display: inline-block; max-width: 650px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
            h1 { color: #38bdf8; font-size: 32px; margin-bottom: 10px; }
            p { color: #94a3b8; font-size: 18px; margin-bottom: 30px; }
            .btn { background: #22c55e; color: white; padding: 18px 36px; font-size: 20px; text-decoration: none; border-radius: 10px; font-weight: bold; display: inline-block; transition: 0.3s; }
            .btn:hover { background: #16a34a; transform: scale(1.03); }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🚀 Super Robô Klebee V144</h1>
            <p>Gerador Autônomo de Vídeos Curtos na Nuvem</p>
            <a class="btn" href="/render?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461">🟢 GERAR VÍDEO DO TIKTOK</a>
        </div>
    </body>
    </html>
    """


@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}


@app.get("/version")
def version():
    return {
        "app_version": APP_VERSION,
        "caption_mode": "word-boundary-highlight",
        "headline_y": HEADLINE_Y,
        "caption_y": CAPTION_Y,
    }


@app.get("/render")
def render(video_url: str = Query(
    "https://www.tiktok.com/@carey_collections/video/7688751450901597461"
), headline: str = Query("ACHADINHO INCRÍVEL!")):
    clips_to_close = []
    try:
        video_path = baixar_video_tiktok(video_url)
        base_clip = VideoFileClip(video_path)
        clips_to_close.append(base_clip)

        script_texto = (
            "Olha esse achadinho incrível para sua casa! Prático, moderno e vai "
            "facilitar demais a sua rotina. Corre no link da bio e garanta o seu "
            "antes que esgote!"
        )
        audio_voz_path, word_events = asyncio.run(gerar_audio_com_timestamps(script_texto))
        narracao_audio = AudioFileClip(audio_voz_path)
        clips_to_close.append(narracao_audio)
        duracao_alvo = float(narracao_audio.duration)

        if base_clip.duration < duracao_alvo:
            repeats = int(duracao_alvo / max(base_clip.duration, 0.1)) + 1
            video_base = concatenate_videoclips([base_clip] * repeats, method="compose").subclip(0, duracao_alvo)
        else:
            video_base = base_clip.subclip(0, duracao_alvo)
        clips_to_close.append(video_base)

        video_base = video_base.resize(height=HEIGHT) if video_base.h / video_base.w < HEIGHT / WIDTH else video_base.resize(width=WIDTH)
        if video_base.w < WIDTH or video_base.h < HEIGHT:
            video_base = video_base.resize(height=HEIGHT)
        video_base = video_base.crop(
            x_center=video_base.w / 2, y_center=video_base.h / 2,
            width=WIDTH, height=HEIGHT
        )

        if base_clip.audio is not None:
            source_audio = base_clip.audio
            if source_audio.duration < duracao_alvo:
                count = int(duracao_alvo / max(source_audio.duration, 0.1)) + 1
                music = concatenate_audioclips([source_audio] * count).subclip(0, duracao_alvo)
            else:
                music = source_audio.subclip(0, duracao_alvo)
            music = music.fx(volumex, 0.12).fx(audio_fadein, 0.25).fx(audio_fadeout, min(0.6, duracao_alvo/3))
            audio_final = CompositeAudioClip([narracao_audio.fx(volumex, 1.0), music]).set_duration(duracao_alvo)
            clips_to_close.extend([music, audio_final])
        else:
            audio_final = narracao_audio.fx(volumex, 1.0).set_duration(duracao_alvo)

        path_head = criar_overlay_headline(headline)
        headline_clip = ImageClip(path_head).set_start(0).set_duration(duracao_alvo).set_pos(("center", HEADLINE_Y))
        clips_to_close.append(headline_clip)

        caption_clips = montar_clips_legenda(word_events, duracao_alvo)
        clips_to_close.extend(caption_clips)
        video_final = CompositeVideoClip([video_base, headline_clip] + caption_clips,
                                         size=(WIDTH, HEIGHT)).set_duration(duracao_alvo).set_audio(audio_final)
        clips_to_close.append(video_final)

        output_name = f"klebee_dynamic_v1_{os.urandom(4).hex()}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_name)
        video_final.write_videofile(
            output_path, fps=24, codec="libx264", audio_codec="aac",
            preset="ultrafast", threads=2, logger=None,
            ffmpeg_params=["-movflags", "+faststart"]
        )
        return FileResponse(output_path, media_type="video/mp4", filename=output_name)
    except Exception as exc:
        return {"status": "ERRO_RENDER", "detalhe": str(exc)}
    finally:
        for clip in reversed(clips_to_close):
            try:
                clip.close()
            except Exception:
                pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
