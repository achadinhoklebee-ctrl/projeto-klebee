import os
import logging
import subprocess
from flask import Flask, jsonify, send_from_directory
from gtts import gTTS

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criação obrigatória da instância do Flask ANTES de qualquer rota
app = Flask(__name__)

# Diretório temporário para processamento
TEMP_DIR = "/tmp"

@app.route("/")
def home():
    return jsonify({"status": "online", "mensagem": "API de geração de vídeos ativa!"})

@app.route("/gerar-demo")
def gerar_demo():
    try:
        logger.info("[DIAGNÓSTICO] Iniciando teste controlado do FFmpeg...")
        
        # 1. Gerar áudio com gTTS
        tts = gTTS(text="Teste de diagnóstico.", lang="pt")
        audio_path = os.path.join(TEMP_DIR, "audio_teste.mp3")
        tts.save(audio_path)
        
        video_final = os.path.join(TEMP_DIR, "video_final.mp4")
        
        # Remover arquivo anterior se existir
        if os.path.exists(video_final):
            os.remove(video_final)

        # 2. Comando mínimo com duração explícita na fonte e thread única para isolar recursos
        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=1080x1920:r=30:d=5",
            "-i", audio_path,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-threads", "1",
            "-t", "5",
            "-shortest",
            video_final
        ]
        
        logger.info(f"[DIAGNÓSTICO] Executando comando: {' '.join(cmd_ffmpeg)}")
        res_ffmpeg = subprocess.run(cmd_ffmpeg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # 3. Coletar evidências reais do resultado
        returncode = res_ffmpeg.returncode
        stderr_completo = res_ffmpeg.stderr[-1000:] if res_ffmpeg.stderr else "Nenhum stderr"
        arquivo_existe = os.path.exists(video_final)
        tamanho_arquivo = os.path.getsize(video_final) if arquivo_existe else 0
        
        logger.info(f"[DIAGNÓSTICO] Returncode: {returncode}")
        logger.info(f"[DIAGNÓSTICO] Arquivo existe: {arquivo_existe} | Tamanho: {tamanho_arquivo} bytes")
        logger.info(f"[DIAGNÓSTICO] Últimas linhas do FFmpeg stderr:\n{stderr_completo}")
        
        if returncode != 0 or not arquivo_existe or tamanho_arquivo == 0:
            return jsonify({
                "status": "erro",
                "returncode": returncode,
                "stderr_parcial": stderr_completo,
                "arquivo_existe": arquivo_existe,
                "tamanho": tamanho_arquivo
            }), 500
            
        return jsonify({
            "status": "sucesso",
            "tamanho_bytes": tamanho_arquivo,
            "download": "/download/video_final.mp4"
        })

    except Exception as e:
        logger.error(f"[EXCEÇÃO CRÍTICA] {str(e)}")
        return jsonify({"status": "erro", "detalhe": str(e)}), 500

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
