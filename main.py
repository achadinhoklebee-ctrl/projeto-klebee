import os
import hashlib
import asyncio
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
from moviepy.audio.fx.all import audio_fadein, audio_fadeout, volumex

app = FastAPI(title="Klebee Cloud Engine - V144")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "videos")
CACHE_AUDIO_DIR = os.path.join(BASE_DIR, "cache_audio")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_AUDIO_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Super Robô Klebee - Cloud Engine V144</title>
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
            <p>Gerador Autônomo de Vídeos Curtos na Nuvem (Com Audio Ducking & Legendas Nítidas)</p>
            <a class="btn" href="/render?produto=organizador%20gaveta%20bambu%20expansivel">🟢 GERAR VÍDEO PERFEITO</a>
        </div>
    </body>
    </html>
    """

async def gerar_audio_narracao(texto):
    hash_txt = hashlib.md5(texto.encode()).hexdigest()
    path_audio = os.path.join(CACHE_AUDIO_DIR, f"{hash_txt}.mp3")
    
    if os.path.exists(path_audio) and os.path.getsize(path_audio) > 100:
        return path_audio

    communicate = edge_tts.Communicate(texto, "pt-BR-AntonioNeural", rate="+15%")
    await communicate.save(path_audio)
    return path_audio

def criar_overlay_texto_flutuante(texto, largura=1080, altura=250, cor_texto="yellow", tamanho_fonte=62):
    img = Image.new('RGBA', (largura, altura), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "arial.ttf",
        "arialbd.ttf"
    ]
    font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, tamanho_fonte)
                break
            except:
                pass
    if not font:
        font = ImageFont.load_default()

    centro_x = largura // 2
    centro_y = altura // 2
    
    raio_borda = 4
    for dx in range(-raio_borda, raio_borda + 1):
        for dy in range(-raio_borda, raio_borda + 1):
            if dx != 0 or dy != 0:
                draw.text((centro_x + dx, centro_y + dy), texto, font=font, fill="black", anchor="mm")
                
    draw.text((centro_x, centro_y), texto, font=font, fill=cor_texto, anchor="mm")
    
    filename = f"temp_txt_{abs(hash(texto))}.png"
    path_img = os.path.join(CACHE_AUDIO_DIR, filename)
    img.save(path_img)
    return path_img

@app.get("/render")
def render(produto: str = "organizador gaveta bambu expansivel"):
    video_path = os.path.join(BASE_DIR, "base.mp4")
    if not os.path.exists(video_path):
        return {"status": "ERRO", "detalhe": "Certifique-se de incluir o arquivo base.mp4 no repositório do GitHub."}

    try:
        base_clip = VideoFileClip(video_path)
        duracao_alvo = 15.0
        
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

        script_texto = "Gaveta bagunçada? Nunca mais! Conheça o organizador em bambu que expande e ajusta perfeitamente na sua casa. Garanta o seu no link!"
        audio_voz_path = asyncio.run(gerar_audio_narracao(script_texto))
        narração_audio = AudioFileClip(audio_voz_path)

        if base_clip.audio is not None:
            trilha_fundo = base_clip.audio.subclip(0, duracao_alvo).fx(volumex, 0.15)
            audio_final = CompositeAudioClip([narração_audio.fx(volumex, 1.2), trilha_fundo])
        else:
            audio_final = narração_audio.fx(volumex, 1.2)

        t1 = ImageClip(criar_overlay_texto_flutuante("🚨 GAVETA BAGUNÇADA?", cor_texto="#FACC15", tamanho_fonte=65)).set_start(0.0).set_duration(2.8).set_pos(('center', 300))
        t2 = ImageClip(criar_overlay_texto_flutuante("🔥 NUNCA MAIS!", cor_texto="#FFFFFF", tamanho_fonte=70)).set_start(2.8).set_duration(2.2).set_pos(('center', 300))
        t3 = ImageClip(criar_overlay_texto_flutuante("📏 EXPANDE E AJUSTA TUDO!", cor_texto="#FACC15", tamanho_fonte=60)).set_start(5.0).set_duration(4.0).set_pos(('center', 1450))
        t4 = ImageClip(criar_overlay_texto_flutuante("⚡ ORGANIZAÇÃO EM SEGUNDOS", cor_texto="#FFFFFF", tamanho_fonte=58)).set_start(9.0).set_duration(3.0).set_pos(('center', 1450))
        t5 = ImageClip(criar_overlay_texto_flutuante("👇 CLIQUE NO LINK E GARANTA O SEU!", cor_texto="#22C55E", tamanho_fonte=55)).set_start(12.0).set_duration(3.0).set_pos(('center', 1600))

        video_final = CompositeVideoClip([video_base, t1, t2, t3, t4, t5], size=(1080, 1920))
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
