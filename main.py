import os
import subprocess
import logging
import threading
from flask import Flask, jsonify, send_from_directory
from gtts import gTTS

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

TEMP_DIR = "/tmp"
OUTPUT_DIR = "/tmp/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def validar_mp4_com_ffprobe(caminho_arquivo):
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
            logger.error(f"[FFPROBE ERRO] {res.stderr}")
            return False
    except Exception as e:
        logger.error(f"[FFPROBE EXCEÇÃO] {str(e)}")
        return False

def renderizar_video_demo():
    try:
        logger.info("[WORKER] Iniciando processamento de vídeo de teste...")
        caminho_audio = os.path.join(TEMP_DIR, "narracao.mp3")
        caminho_saida = os.path.join(OUTPUT_DIR, "video_final.mp4")

        texto = "Atenção para essa super promoção do Projeto Klebee! Garanta já o seu produto no link abaixo."
        tts = gTTS(text=texto, lang='pt', slow=False)
        tts.save(caminho_audio)
        logger.info("[TTS] Narração sintetizada com sucesso!")

        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=0x1e1e2e:s=1080x1920:d=10",
            "-i", caminho_audio,
            "-vf", "drawtext=text='PROJETO KLEBEE':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-preset", "ultrafast", "-threads", "1",
            "-c:a", "aac", "-b:a", "128k", "-shortest",
            caminho_saida
        ]
        
        logger.info("[FFMPEG] Executando renderização...")
        res = subprocess.run(cmd_ffmpeg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if res.returncode != 0:
            logger.error(f"[FFMPEG ERRO] {res.stderr}")
            return

        if validar_mp4_com_ffprobe(caminho_saida):
            logger.info(f"[SUCESSO] Vídeo pronto em: {caminho_saida}")
        else:
            logger.error("[FALHA] Arquivo final inválido.")

    except Exception as e:
        logger.error(f"[WORKER EXCEÇÃO] {str(e)}")

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
    threading.Thread(target=renderizar_video_demo, daemon=True).start()
    return jsonify({
        "status": "processando",
        "mensagem": "Renderização iniciada em segundo plano!"
    })

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(OUTPUT_DIR, filename)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=porta)
