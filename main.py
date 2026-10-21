import os
import subprocess
import logging
import threading
import time
from flask import Flask, jsonify, send_from_directory
from gtts import gTTS

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

TEMP_DIR = "/tmp"
OUTPUT_DIR = "/tmp/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def validar_mp4_com_ffprobe(caminho_arquivo):
    """Valida se o vídeo gerado pelo FFmpeg está íntegro e reproduzível."""
    if not os.path.exists(caminho_arquivo):
        logger.error(f"[FFPROBE] Arquivo não encontrado: {caminho_arquivo}")
        return False
    
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nohash=1",
        caminho_arquivo
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0 and len(res.stdout.strip()) > 0:
            logger.info(f"[FFPROBE OK] Vídeo válido! Duração: {res.stdout.strip()}s")
            return True
        else:
            logger.error(f"[FFPROBE ERRO] Falha no arquivo: {res.stderr}")
            return False
    except Exception as e:
        logger.error(f"[FFPROBE EXCEÇÃO] {str(e)}")
        return False

def renderizar_video_demo():
    """Worker em segundo plano para sintetizar áudio e aplicar audio ducking no FFmpeg."""
    try:
        logger.info("[WORKER] Iniciando processamento de vídeo de teste...")
        
        caminho_audio = os.path.join(TEMP_DIR, "narracao.mp3")
        caminho_saida = os.path.join(OUTPUT_DIR, "video_final.mp4")

        # 1. Gerar narração em Português
        texto = "Atenção para essa super promoção do Projeto Klebee! Garanta já o seu produto no link abaixo."
        tts = gTTS(text=texto, lang='pt', slow=False)
        tts.save(caminho_audio)
        logger.info("[TTS] Narração em português sintetizada com sucesso!")

        # 2. Gerar vídeo sintético de 10s com áudio integrado via FFmpeg
        # Cria um vídeo vertical 1080x1920 com fundo colorido, texto e a narração embutida
        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=0x1e1e2e:s=1080x1920:d=10",
            "-i", caminho_audio,
            "-vf", "drawtext=text='PROJETO KLEBEE':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-preset", "ultrafast", "-threads", "1",
            "-c:a", "aac", "-b:a", "128k", "-shortest",
            caminho_saida
        ]
        
        logger.info("[FFMPEG] Executando comando de renderização...")
        res = subprocess.run(cmd_ffmpeg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if res.returncode != 0:
            logger.error(f"[FFMPEG ERRO] {res.stderr}")
            return

        # 3. Validar resultado final com FFprobe
        if validar_mp4_com_ffprobe(caminho_saida):
            logger.info(f"[SUCESSO] Vídeo gerado e pronto em: {caminho_saida}")
        else:
            logger.error("[FALHA] O arquivo final gerado é inválido.")

    except Exception as e:
        logger.error(f"[WORKER EXCEÇÃO] Erro inesperado: {str(e)}")

@app.route("/")
def index():
    return jsonify({
        "status": "online",
        "projeto": "Projeto Klebee",
        "endpoints": {
            "gerar_demo": "/gerar-demo",
            "baixar_video": "/download/video_final.mp4"
        }
    })

@app.route("/gerar-demo")
def disparar_geracao():
    """Gatilho leve que aciona a fábrica em background sem travar o painel."""
    threading.Thread(target=renderizar_video_demo, daemon=True).start()
    return jsonify({
        "status": "processando",
        "mensagem": "A fábrica iniciou a renderização em segundo plano. Verifique o log no Railway!"
    })

@app.route("/download/<filename>")
def download_file(filename):
    """Entrega o vídeo final direto do diretório temporário."""
    return send_from_directory(OUTPUT_DIR, filename)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=porta)
