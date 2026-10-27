import os
import re
import hashlib
import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, ImageClip,
    CompositeAudioClip, concatenate_videoclips, concatenate_audioclips
)
from moviepy.audio.fx.all import volumex, audio_fadein, audio_fadeout

APP_VERSION = "KLEBEE-ASS-KARAOKE-QA-2026-10-27-01"
app = FastAPI(title="Klebee Cloud Engine - Dynamic Captions", version=APP_VERSION)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "videos")
CACHE_AUDIO_DIR = os.path.join(BASE_DIR, "cache_audio")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_AUDIO_DIR, exist_ok=True)

WIDTH, HEIGHT = 1080, 1920
VOICE = "pt-BR-AntonioNeural"
VOICE_RATE = "+15%"
# Ajustáveis conforme a interface da Shopee.
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
        raise RuntimeError("O Edge TTS não retornou eventos WordBoundary; não é possível garantir sincronização por palavra.")
    return audio_path, words


def limpar_texto_visual(texto: str) -> str:
    texto = re.sub(r"[\U0001F000-\U0001FAFF\U00002600-\U000027BF]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def ass_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def ass_safe(text: str) -> str:
    text = limpar_texto_visual(str(text))
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def criar_legendas_ass(words, duration: float, headline: str, ass_path: str) -> int:
    valid = []
    for w in words:
        txt = ass_safe(w.get("text", ""))
        try:
            start, end = float(w["start"]), float(w["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if txt and 0 <= start < duration and end > start:
            valid.append({"text": txt, "start": start, "end": min(duration, end)})
    valid.sort(key=lambda x: x["start"])
    if not valid:
        raise RuntimeError("Validação falhou: não há timestamps de palavras válidos para as legendas.")

    header = r'''[Script Info]
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Headline,DejaVu Sans,78,&H0000E5FF,&H0000E5FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,2,5,70,70,0,1
Style: Karaoke,DejaVu Sans,60,&H0000E5FF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,2,5,70,70,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events = []
    clean_head = ass_safe(headline)
    if clean_head:
        title_words = clean_head.split()
        lines, line = [], []
        for word in title_words:
            if len(" ".join(line + [word])) > 22 and line:
                lines.append(" ".join(line)); line = [word]
            else:
                line.append(word)
        if line: lines.append(" ".join(line))
        title_text = r"\N".join(lines[:2])
        events.append(f"Dialogue: 2,{ass_time(0)},{ass_time(duration)},Headline,,0,0,0,,{{\\an5\\pos(540,220)}}{title_text}")

    group_size = 4
    for offset in range(0, len(valid), group_size):
        group = valid[offset:offset + group_size]
        start = group[0]["start"]
        if offset + group_size < len(valid):
            end = max(group[-1]["end"], valid[offset + group_size]["start"])
        else:
            end = max(group[-1]["end"], min(duration, group[-1]["start"] + 0.25))
        end = min(duration, max(start + 0.08, end))
        chunks = []
        for i, word in enumerate(group):
            next_start = group[i + 1]["start"] if i + 1 < len(group) else end
            cs = max(1, round(max(0.01, next_start - word["start"]) * 100))
            chunks.append(f"{{\\k{cs}}}{word['text']}")
        text_line = " ".join(chunks)
        events.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},Karaoke,,0,0,0,,{{\\an5\\pos(540,1320)}}{text_line}")

    with open(ass_path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write(header + "\n".join(events) + "\n")
    if len(events) < 2:
        raise RuntimeError("Validação falhou: o arquivo ASS não contém headline e legendas.")
    return len(valid)


def validar_mp4(path: str, min_size: int = 100_000):
    if not os.path.exists(path) or os.path.getsize(path) < min_size:
        raise RuntimeError("Validação do vídeo falhou: arquivo ausente ou pequeno demais.")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height", "-of", "json", path],
        capture_output=True, text=True, timeout=20
    )
    if probe.returncode != 0:
        raise RuntimeError("Validação do vídeo falhou: ffprobe não conseguiu ler o MP4.")
    import json
    data = json.loads(probe.stdout or "{}")
    streams = data.get("streams", [])
    if not any(s.get("codec_type") == "video" for s in streams):
        raise RuntimeError("Validação do vídeo falhou: MP4 sem faixa de vídeo.")
    if not any(s.get("codec_type") == "audio" for s in streams):
        raise RuntimeError("Validação do vídeo falhou: MP4 sem faixa de áudio.")
    return {"bytes": os.path.getsize(path), "streams": streams, "duration": data.get("format", {}).get("duration")}


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
        "caption_mode": "ASS-karaoke-word-highlight",
        "render_validation": "ffprobe + nonempty output + burned subtitles",
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

        output_name = f"klebee_ass_karaoke_{os.urandom(4).hex()}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_name)
        raw_path = os.path.join(OUTPUT_DIR, f"raw_{output_name}")
        ass_path = os.path.join(CACHE_AUDIO_DIR, f"subs_{os.urandom(4).hex()}.ass")

        video_final = CompositeVideoClip([video_base], size=(WIDTH, HEIGHT)).set_duration(duracao_alvo).set_audio(audio_final)
        clips_to_close.append(video_final)
        video_final.write_videofile(
            raw_path, fps=24, codec="libx264", audio_codec="aac",
            preset="ultrafast", threads=2, logger=None,
            ffmpeg_params=["-movflags", "+faststart"]
        )

        total_words = criar_legendas_ass(word_events, duracao_alvo, headline, ass_path)
        ass_filter_path = ass_path.replace("\\", "/").replace(":", r"\\:").replace("'", r"\\'")
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", raw_path,
            "-vf", f"ass='{ass_filter_path}'",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-c:a", "copy", "-movflags", "+faststart", output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        if result.returncode != 0:
            raise RuntimeError("FFmpeg/libass não conseguiu aplicar as legendas: " + (result.stderr[-1200:] or "erro desconhecido"))
        
        qa = validar_mp4(output_path)
        report_path = output_path + ".qa.json"
        import json
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({"version": APP_VERSION, "caption_engine": "ASS karaoke", "word_count": total_words, "headline": headline, "validation": qa}, f, ensure_ascii=False, indent=2)
        
        try:
            os.remove(raw_path)
            os.remove(ass_path)
        except OSError:
            pass

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
