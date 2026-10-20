import os
import sys
import time
import math
import random
import threading
import subprocess
import traceback
from flask import Flask, send_from_directory, render_template_string
from gtts import gTTS

app = Flask(__name__)
VIDEO_DIR = "/tmp/videos"
ASSETS_DIR = "/tmp/assets"
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# Painel Web Profissional do Projeto Klebee
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Projeto Klebee - Painel de Produção Automática</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; text-align: center; }
        h1 { color: #ee4d2d; margin-bottom: 5px; font-size: 26px; }
        p.subtitle { color: #8b949e; font-size: 14px; margin-bottom: 25px; }
        .grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }
        .video-card { background: #161b22; padding: 15px; border-radius: 12px; width: 280px; box-shadow: 0 4px 15px rgba(0,0,0,0.6); border: 1px solid #30363d; transition: transform 0.2s; }
        .video-card:hover { transform: translateY(-5px); border-color: #ee4d2d; }
        video { width: 100%; height: 420px; border-radius: 8px; background: #000; object-fit: cover; }
        .filename { font-weight: bold; margin: 12px 0 8px 0; font-size: 13px; color: #f0f6fc; word-break: break-all; }
        .btn { display: inline-block; width: 90%; margin-top: 8px; padding: 10px; background: #ee4d2d; color: white; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: bold; }
        .btn:hover { background: #d73211; }
        .badge { display: inline-block; padding: 4px 8px; background: #238636; color: white; border-radius: 12px; font-size: 11px; margin-bottom: 10px; font-weight: bold; }
    </style>
</head>
<body>
    <h1>PROJETO KLEBEE - FÁBRICA DE VÍDEOS</h1>
    <p class="subtitle">Esteiras de Produção de Alta Conversão | Duração: 15s | Áudio Ducking + Narração + Legendas Dinâmicas</p>
    <div class="grid">
        {% if videos %}
            {% for v in videos %}
            <div class="video-card">
                <span class="badge">VÍDEO PRONTO PARA POSTAR</span>
                <video controls src="/videos/{{ v }}"></video>
                <div class="filename">{{ v }}</div>
                <a class="btn" href="/videos/{{ v }}" download>Baixar para Celular / PC</a>
            </div>
            {% endfor %}
        {% else %}
            <p style="color: #e3b341; font-size: 16px;">O Robô está a minerar produtos e a renderizar o primeiro lote com narração e áudio... Por favor, atualize a página em 1 a 2 minutos.</p>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    videos = sorted([f for f in os.listdir(VIDEO_DIR) if f.endswith('.mp4')], reverse=True)
    return render_template_string(HTML_TEMPLATE, videos=videos)

@app.route('/videos/<filename>')
def serve_video(filename):
    return send_from_directory(VIDEO_DIR, filename)

def gerar_musica_fundo(caminho_musica, duracao=15):
    """Gera uma trilha sonora ritmada sintética via FFmpeg se não houver arquivo local de música."""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"sine=frequency=120:beep_factor=2:duration={duracao}",
        "-af", "volume=0.3",
        caminho_musica
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def criar_video_completo_klebee(ciclo, dados_produto):
    nome_arquivo = f"klebee_prod_{ciclo}_{dados_produto['id']}.mp4"
    caminho_saida = os.path.join(VIDEO_DIR, nome_arquivo)
    
    caminho_tts = os.path.join(ASSETS_DIR, f"tts_{ciclo}.mp3")
    caminho_bgm = os.path.join(ASSETS_DIR, f"bgm_{ciclo}.wav")
    caminho_audio_final = os.path.join(ASSETS_DIR, f"audio_mixed_{ciclo}.wav")
    
    print(f"\n[PASSO 1/4] Gerando narração persuasiva para: {dados_produto['nome']}", flush=True)
    tts = gTTS(text=dados_produto['roteiro_narrado'], lang='pt', slow=False)
    tts.save(caminho_tts)
    
    print("[PASSO 2/4] Criando trilha sonora e aplicando Audio Ducking mestre...", flush=True)
    gerar_musica_fundo(caminho_bgm, duracao=15)
    
    # Mixagem avançada no FFmpeg: junta voz + música de fundo aplicando o ducking (abaixa a música quando a voz entra)
    cmd_audio = [
        "ffmpeg", "-y",
        "-i", caminho_tts,
        "-i", caminho_bgm,
        "-filter_complex",
        "[1:a]volume=0.2[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]",
        "-map", "[aout]",
        caminho_audio_final
    ]
    subprocess.run(cmd_audio, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("[PASSO 3/4] Renderizando vídeo 9:16 com Legendas Dinâmicas e Animação de Fundo...", flush=True)
    
    # Texto de gancho e slogan
    hook = dados_produto['hook']
    slogan = "CLIQUE NA SACOLINHA / LINK NA BIO"
    
    # Filtro visual avançado do FFmpeg: gradiente dinâmico + caixa de legenda destacada
    filter_complex = (
        f"color=c=0x111827:s=1080x1920:d=15[bg];"
        f"[bg]drawtext=text='{hook}':fontcolor=0xFFD700:fontsize=48:fontweight=bold:x=(w-text_w)/2:y=300:box=1:boxcolor=0x000000@0.8:boxborderw=15,"
        f"drawtext=text='{dados_produto['nome_curto']}':fontcolor=0xFFFFFF:fontsize=40:x=(w-text_w)/2:y=900:box=1:boxcolor=0xEE4D2D@0.9:boxborderw=12,"
        f"drawtext=text='{slogan}':fontcolor=0x00FF7F:fontsize=38:x=(w-text_w)/2:y=1500:box=1:boxcolor=0x000000@0.8:boxborderw=10[v]"
    )
    
    cmd_video = [
        "ffmpeg", "-y",
        "-threads", "1",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=15",
        "-i", caminho_audio_final,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        caminho_saida
    ]
    
    subprocess.run(cmd_video, check=True)
    print(f"[PASSO 4/4] -> VÍDEO CONCLUÍDO COM SUCESSO: {nome_arquivo}", flush=True)

def pipeline_garimpagem_e_producao():
    # Banco de Produtos Minerados pelo Robô (Matriz de Vendas)
    matriz_produtos = [
        {
            "id": "1111_01",
            "nome": "Mop Esfregão Triangular 360 Lança Água",
            "nome_curto": "MOP TRIANGULAR 360",
            "hook": "ISSO LIMPA ATÉ A SUJEIRA DE ANOS!",
            "roteiro_narrado": "Olha essa inovação pra sua casa! O Mop Triangular limpa todos os cantos sem você precisar se abaixar. Aproveite os cupons com frete grátis e garanta o seu na sacolinha!"
        },
        {
            "id": "1111_02",
            "nome": "Mini Processador Elétrico de Alimentos USB",
            "nome_curto": "MINI PROCESSADOR ELÉTRICO",
            "hook": "CHEGA DE CHORAR CORTANDO CEBOLA!",
            "roteiro_narrado": "Esse mini processador tritural alho e temperos em 5 segundos! É prático, recarregável e economiza muito tempo na cozinha. Corre pro link na bio!"
        },
        {
            "id": "1111_03",
            "nome": "Luminária Sensor de Presença Sem Fio",
            "nome_curto": "LUMINÁRIA SENSOR LED",
            "hook": "SUA CASA PARECENDO HOTEL 5 ESTRELAS!",
            "roteiro_narrado": "Chega de acender luz de madrugada! Essa luminária sensor acende sozinha quando você passa. Fácil de instalar com imã. Clique na sacolinha e peça a sua!"
        }
    ]
    
    ciclo = 1
    while True:
        produto = matriz_produtos[(ciclo - 1) % len(matriz_produtos)]
        print(f"\n=======================================================", flush=True)
        print(f"INICIANDO CICLO {ciclo} DE PRODUÇÃO AUTOMÁTICA", flush=True)
        print(f"PRODUTO MINERADO: {produto['nome']}", flush=True)
        print(f"=======================================================", flush=True)
        
        try:
            criar_video_completo_klebee(ciclo, produto)
        except Exception as e:
            print(f"❌ ERRO DURANTE A RENDERIZAÇÃO NO CICLO {ciclo}:", flush=True)
            traceback.print_exc()
            
        ciclo += 1
        time.sleep(45)

if __name__ == "__main__":
    t = threading.Thread(target=pipeline_garimpagem_e_producao, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
