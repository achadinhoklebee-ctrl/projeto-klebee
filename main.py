import os
import logging
import subprocess
from flask import Flask, jsonify, send_from_directory
from gtts import gTTS

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Diretório temporário para processamento
TEMP_DIR = "/tmp"

@app.route("/")
def home():
    return jsonify({"status": "online", "mensagem": "API de geração de vídeos ativa!"})

@app.route("/gerar-demo")
def gerar_demo():
    try:
        logger.info("[WORKER] Iniciando processamento de vídeo de teste...")
        
        # 1. Gerar áudio com gTTS
        tts = gTTS(text="Olá! Este é um teste automatizado de vídeo no Railway.", lang="pt")
        audio_path = os.path.join(TEMP_DIR, "audio_teste.mp3")
        tts.save(audio_path)
        logger.info("[TTS] Narração sintetizada com sucesso!")
        
        # 2. Caminho do vídeo final
        video_final = os.path.join(TEMP_DIR, "video_final.mp4")
        
        # 3. Renderizar com FFmpeg (com o parâmetro -shortest para fechar no fim do áudio)
        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=1080x1920:r=30",
            "-i", audio_path,
            "-c:v", "libx264", "-t", "5",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            video_final
        ]
        
        logger.info("[FFMPEG] Executando renderização...")
        res_ffmpeg = subprocess.run(cmd_ffmpeg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if res_ffmpeg.returncode != 0:
            logger.error(f"[FFMPEG ERRO] {res_ffmpeg.stderr}")
            return jsonify({"status": "erro", "mensagem": "Falha na renderização FFmpeg"}), 500
            
        # 4. Validar com ffprobe
        if validar_mp4_com_ffprobe(video_final):
            return jsonify({"status": "sucesso", "mensagem": "Vídeo gerado e validado com sucesso!", "download": "/download/video_final.mp4"})
        else:
            logger.error("[FALHA] Arquivo final inválido.")
            return jsonify({"status": "erro", "mensagem": "Arquivo gerado é inválido"}), 500

    except Exception as e:
        logger.error(f"[EXCEÇÃO] {str(e)}")
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

def validar_mp4_com_ffprobe(caminho_arquivo):
    if not os.path.exists(caminho_arquivo):
        logger.error(f"[FFPROBE] Arquivo não encontrado: {caminho_arquivo}")
        return False
    
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1",
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

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(TEMP_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=porta)
