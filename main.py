import os
import sys
import time
import threading
import subprocess
import traceback
from flask import Flask, send_from_directory, render_template_string

app = Flask(__name__)
VIDEO_DIR = "/tmp/videos"
os.makedirs(VIDEO_DIR, exist_ok=True)

# Página web simples e limpa para você assistir e validar os vídeos
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel de Validação - Achadinhos Shopee</title>
    <style>
        body { font-family: Arial, sans-serif; background: #121212; color: #fff; padding: 20px; text-align: center; }
        h1 { color: #ff5722; }
        .grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 20px; }
        .video-card { background: #1e1e1e; padding: 15px; border-radius: 8px; width: 280px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        video { width: 100%; border-radius: 4px; background: #000; }
        .filename { font-weight: bold; margin-bottom: 10px; word-break: break-all; font-size: 14px; color: #ccc; }
        .btn { display: inline-block; margin-top: 10px; padding: 8px 12px; background: #ff5722; color: white; text-decoration: none; border-radius: 4px; font-size: 12px; }
        .btn:hover { background: #e64a19; }
    </style>
</head>
<body>
    <h1>Painel de Validação de Vídeos</h1>
    <p>Assista aos vídeos gerados pelo robô, valide e baixe antes de postar.</p>
    <div class="grid">
        {% if videos %}
            {% for v in videos %}
            <div class="video-card">
                <div class="filename">{{ v }}</div>
                <video controls src="/videos/{{ v }}"></video>
                <br>
                <a class="btn" href="/videos/{{ v }}" download>Baixar Vídeo</a>
            </div>
            {% endfor %}
        {% else %}
            <p>Gerando o primeiro vídeo... Atualize a página em instantes.</p>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    # Lista os vídeos gerados do mais recente para o mais antigo
    videos = sorted([f for f in os.listdir(VIDEO_DIR) if f.endswith('.mp4')], reverse=True)
    return render_template_string(HTML_TEMPLATE, videos=videos)

@app.route('/videos/<filename>')
def serve_video(filename):
    return send_from_directory(VIDEO_DIR, filename)

def gerar_videos_em_background():
    ciclo = 1
    while True:
        print(f"\n--- [CICLO {ciclo}] Gerando vídeo ---", flush=True)
        nome_arquivo = f"shopee_video_{ciclo}.mp4"
        caminho_saida = os.path.join(VIDEO_DIR, nome_arquivo)
        
        comando = [
            "ffmpeg", "-y",
            "-threads", "1",
            "-f", "lavfi", "-i", "color=c=navy:s=1080x1920:d=5",
            "-vf", "drawtext=text='ACHADINHOS SHOPEE':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-preset", "ultrafast", "-threads", "1", "-pix_fmt", "yuv420p",
            caminho_saida
        ]
        
        try:
            subprocess.run(comando, check=True)
            print(f"-> Vídeo {nome_arquivo} gerado com sucesso!", flush=True)
        except Exception as e:
            print(f"Erro no FFmpeg: {e}", flush=True)
            
        ciclo += 1
        time.sleep(60)

if __name__ == "__main__":
    # Inicia a geração de vídeos em segundo plano
    t = threading.Thread(target=gerar_videos_em_background, daemon=True)
    t.start()
    
    # Inicia o servidor web do painel
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
