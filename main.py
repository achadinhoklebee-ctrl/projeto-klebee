import os
import hashlib
import asyncio
import subprocess
import textwrap
import numpy as np
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, FileResponse
import edge_tts
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    CompositeAudioClip,
    concatenate_videoclips
)
from moviepy.audio.fx.all import volumex

app = FastAPI(title="Klebee Cloud Engine - V144 Pro Viral")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "videos")
CACHE_AUDIO_DIR = os.path.join(BASE_DIR, "cache_audio")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_AUDIO_DIR, exist_ok=True)

def baixar_video_tiktok(url_tiktok):
    hash_url = hashlib.md5(url_tiktok.encode()).hexdigest()
    output_path = os.path.join(CACHE_AUDIO_DIR, f"base_{hash_url}.mp4")
    
    if os.path.exists(output_path) and os.path.getsize(output_path) > 100000:
        return output_path

    cmd = [
        "yt-dlp",
        "-f", "b",
        "-o", output_path,
        url_tiktok
    ]
    subprocess.run(cmd, check=True)
    return output_path

async def gerar_audio_narracao(texto):
    hash_txt = hashlib.md5(texto.encode()).hexdigest()
    path_audio = os.path.join(CACHE_AUDIO_DIR, f"{hash_txt}.mp3")
    
    if os.path.exists(path_audio) and os.path.getsize(path_audio) > 100:
        return path_audio

    communicate = edge_tts.Communicate(texto, "pt-BR-AntonioNeural", rate="+15%")
    await communicate.save(path_audio)
    return path_audio

def carregar_fonte(tamanho):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "arial.ttf",
        "arialbd.ttf"
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, tamanho)
            except:
                pass
    return ImageFont.load_default()

def criar_overlay_headline(texto, largura=1080, altura=240):
    """Gera uma headline profissional superior grande, marcante e com contorno forte."""
    img = Image.new('RGBA', (largura, altura), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = carregar_fonte(72)  # Aumentado para ter alto impacto visual
    
    linhas = textwrap.wrap(texto, width=20)
    centro_x = largura // 2
    
    current_y = 15
    for linha in linhas:
        bbox = font.getbbox(linha)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        line_x = centro_x - (w // 2)
        
        # Contorno / Sombra preta grossa
        offset = 4
        for dx in range(-offset, offset + 1):
            for dy in range(-offset, offset + 1):
                if dx != 0 or dy != 0:
                    draw.text((line_x + dx, current_y + dy), linha, font=font, fill=(0, 0, 0, 255))
        
        # Texto principal em Amarelo Vivo
        draw.text((line_x, current_y), linha, font=font, fill="#FACC15")
        current_y += h + 10
        
    path_img = os.path.join(CACHE_AUDIO_DIR, f"headline_{abs(hash(texto))}.png")
    img.save(path_img)
    return path_img

def criar_overlay_legenda_dinamica(texto, largura=1080, altura=280, cor_texto="#FFFFFF"):
    """Gera legenda dinâmica inferior com pill translúcida compacta e quebra automática real."""
    linhas = textwrap.wrap(texto, width=26)
    img = Image.new('RGBA', (largura, altura), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = carregar_fonte(52)
    
    pad_x = 35
    pad_y = 18
    
    line_widths = []
    line_heights = []
    for linha in linhas:
        bbox = font.getbbox(linha)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])
    
    max_w = max(line_widths) if line_widths else 100
    total_h = sum(line_heights) + (len(linhas) - 1) * 10
    
    box_w = max_w + (pad_x * 2)
    box_h = total_h + (pad_y * 2)
    box_x = (largura - box_w) // 2
    box_y = (altura - box_h) // 2
    
    # Pill translúcida elegante
    draw.rounded_rectangle(
        [box_x, box_y, box_x + box_w, box_y + box_h],
        radius=16,
        fill=(0, 0, 0, 210)
    )
    
    current_y = box_y + pad_y
    for i, linha in enumerate(linhas):
        w = line_widths[i]
        h = line_heights[i]
        line_x = box_x + (box_w - w) // 2
        
        offset = 3
        for dx in range(-offset, offset + 1):
            for dy in range(-offset, offset + 1):
                if dx != 0 or dy != 0:
                    draw.text((line_x + dx, current_y + dy), linha, font=font, fill=(0, 0, 0, 255))
        
        draw.text((line_x, current_y), linha, font=font, fill=cor_texto)
        current_y += h + 10
        
    path_img = os.path.join(CACHE_AUDIO_DIR, f"leg_{abs(hash(texto))}.png")
    img.save(path_img)
    return path_img

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
            <h1>🚀 Super Robô Klebee V144 Pro</h1>
            <p>Gerador Autônomo de Vídeos Curtos na Nuvem</p>
            <a class="btn" href="/render?video_url=https://www.tiktok.com/@carey_collections/video/7688751450901597461">🟢 GERAR VÍDEO PROFISSIONAL</a>
        </div>
    </body>
    </html>
    """

@app.get("/render")
def render(video_url: str = Query("https://www.tiktok.com/@carey_collections/video/7688751450901597461")):
    try:
        video_path = baixar_video_tiktok(video_url)
        base_clip = VideoFileClip(video_path)
        
        script_texto = "Olha esse achadinho incrível para sua casa! Prático, moderno e vai facilitar demais a sua rotina. Corre no link da bio e garanta o seu antes que esgote!"
        audio_voz_path = asyncio.run(gerar_audio_narracao(script_texto))
        narracao_audio = AudioFileClip(audio_voz_path)
        
        duracao_alvo = float(narracao_audio.duration) + 0.5
        
        if base_clip.duration < duracao_alvo:
            repeats = int(duracao_alvo / base_clip.duration) + 1
            video_base = concatenate_videoclips([base_clip] * repeats).subclip(0, duracao_alvo)
        else:
            video_base = base_clip.subclip(0, duracao_alvo)

        video_base = video_base.resize(width=1080)
        if video_base.h > 1920:
            y_c = video_base.h / 2
            video_base = video_base.crop(y1=y_c-960, y2=y_c+960, x1=0, x2=1080)
        elif video_base.h < 1920:
            video_base = video_base.resize((1080, 1920))

        if base_clip.audio is not None:
            trilha_fundo = base_clip.audio.subclip(0, duracao_alvo).fx(volumex, 0.12)
            audio_final = CompositeAudioClip([narracao_audio.fx(volumex, 1.2), trilha_fundo])
        else:
            audio_final = narracao_audio.fx(volumex, 1.2)

        # 1. Headline no topo com tamanho dominante
        path_head = criar_overlay_headline("🚨 ACHADINHO INCRÍVEL!")
        headline_clip = ImageClip(path_head).set_start(0.0).set_duration(duracao_alvo).set_pos(('center', 150))

        # 2. Legendas dinâmicas sincronizadas
        partes_legenda = [
            ("Olha esse achadinho incrível para sua casa!", 0.0, 3.2, "#FFFFFF"),
            ("Prático, moderno e vai facilitar", 3.2, 6.5, "#FACC15"),
            ("demais a sua rotina!", 6.5, 8.8, "#FFFFFF"),
            ("Corre no link da bio e garanta o seu", 8.8, 12.0, "#FACC15"),
            ("antes que esgote!", 12.0, duracao_alvo, "#22C55E")
        ]

        clips_legendas = [headline_clip]
        for texto_bloco, inicio, fim, cor in partes_legenda:
            if inicio >= duracao_alvo:
                continue
            dur = min(fim, duracao_alvo) - inicio
            if dur <= 0:
                continue
            path_leg = criar_overlay_legenda_dinamica(texto_bloco, cor_texto=cor)
            leg_clip = ImageClip(path_leg).set_start(inicio).set_duration(dur).set_pos(('center', 1350))
            clips_legendas.append(leg_clip)

        video_final = CompositeVideoClip([video_base] + clips_legendas, size=(1080, 1920))
        video_final = video_final.set_duration(duracao_alvo).set_audio(audio_final)

        output_name = f"klebee_v144_cloud_{int(os.urandom(3).hex(), 16)}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_name)

        video_final.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="fast",
            threads=4,
            logger=None
        )

        return FileResponse(output_path, media_type="video/mp4", filename=output_name)

    except Exception as e:
        return {"status": "ERRO_RENDER", "detalhe": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
