import os
import subprocess
import logging
from flask import Flask, jsonify

# Configuração de logs detalhados (Diagnóstico)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TEMP_DIR = "/tmp"

def validar_e_diagnosticar_ambiente():
    """1. Diagnóstico do ambiente exigido (FFmpeg, FFprobe e espaço)"""
    logger.info("--- INICIANDO DIAGNÓSTICO DO AMBIENTE ---")
    
    # Verifica FFmpeg e FFprobe
    for ferramenta in ["ffmpeg", "ffprobe"]:
        try:
            res = subprocess.run([ferramenta, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                logger.info(f"[OK] {ferramenta} encontrado: {res.stdout.splitlines()[0]}")
            else:
                logger.error(f"[ERRO] {ferramenta} falhou ao executar.")
        except FileNotFoundError:
            logger.error(f"[CRÍTICO] {ferramenta} NÃO está instalado no container!")

    # Verifica espaço em disco no diretório temporário
    estatisticas_disco = os.statvfs(TEMP_DIR)
    espaco_livre_mb = (estatisticas_disco.f_bavail * estatisticas_disco.f_frsize) / (1024 * 1024)
    logger.info(f"[OK] Espaço livre em {TEMP_DIR}: {espaco_livre_mb:.2f} MB")
    logger.info("--- FIM DO DIAGNÓSTICO ---")

def validar_mp4_com_ffprobe(caminho_arquivo):
    """2. Verificação de integridade do MP4 final com FFprobe"""
    if not os.path.exists(caminho_arquivo):
        logger.error(f"Arquivo final não encontrado no caminho: {caminho_arquivo}")
        return False
    
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nohash=1",
        caminho_arquivo
    ]
    try:
        resultado = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if resultado.returncode == 0 and len(resultado.stdout.strip()) > 0:
            logger.info(f"Sucesso! Vídeo válido. Duração: {resultado.stdout.strip()} segundos.")
            return True
        else:
            logger.error(f"Erro no FFprobe (stderr): {resultado.stderr}")
            return False
    except Exception as e:
        logger.error(f"Exceção ao rodar FFprobe: {str(e)}")
        return False

@app.route("/")
def index():
    validar_e_diagnosticar_ambiente()
    return jsonify({
        "status": "online",
        "projeto": "Projeto Klebee",
        "mensagem": "Worker assíncrono e diagnóstico de FFmpeg ativos!"
    })

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=porta)
