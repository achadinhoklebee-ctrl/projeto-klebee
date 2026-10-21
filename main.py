import os
import logging
import subprocess
import urllib.request
from flask import Flask, jsonify, send_from_directory
from gtts import gTTS

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização obrigatória do Flask antes de qualquer rota
app = Flask(__name__)

TEMP_DIR = "/tmp"

@app.route("/")
def home():
    return jsonify({"status": "online", "mensagem": "Pipeline de vídeos automatizado ativo!"})

@app.route("/gerar-video")
def gerar_video():
    try:
        logger.info("[WORKER] Iniciando pipeline de produção de vídeo...")
        
        video_original = os.path.join(TEMP_DIR, "input_produto.mp4")
        audio_path = os.path.join(TEMP_DIR, "narracao.mp3")
        video_final = os.path.join(TEMP_DIR, "video_afiliado.mp4")
        
        for f in [video_original, audio_path, video_final]:
            if os.path.exists(f):
                os.remove(f)

        logger.info("[BAIXANDO] Obtendo vídeo base do produto com cabeçalhos de navegação...")
        url_video_exemplo = "https://www.w3schools.com/html/mov_bbb.mp4"
        
        # Requisição com User-Agent para contornar o bloqueio 403 Forbidden
        req = urllib.request.Request(
            url_video_exemplo,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req) as response, open(video_original, 'wb') as out_file:
            out_file.write(response.read())

        logger.info("[TTS] Sintetizando narração em português para afiliado...")
        texto_venda = "Olha esse achadinho incrível que eu acabei de encontrar! Corre para garantir o seu clicando no link da sacolinha."
        tts = gTTS(text=texto_venda, lang="pt")
        tts.save(audio_path)

        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-i", video_original,
            "-i", audio_path,
            "-filter_complex", "[0:a]volume=0.2[a1];[1:a]volume=1.0[a2];[a1][a2]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            video_final
        ]
        
        logger.info("[FFMPEG] Renderizando vídeo final de afiliado com ducking de áudio...")
        res_ffmpeg = subprocess.run(cmd_ffmpeg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if res_ffmpeg.returncode != 0:
            logger.error(f"[FFMPEG ERRO] {res_ffmpeg.stderr}")
            return jsonify({"status": "erro", "detalhe": res_ffmpeg.stderr[-500:]}), 500

        if os.path.exists(video_final) and os.path.getsize(video_final) > 0:
            logger.info("[SUCESSO] Vídeo gerado e validado com sucesso!")
            return jsonify({
                "status": "sucesso",
                "mensagem": "Vídeo de afiliado gerado com sucesso!",
                "download": "/download/video_afiliado.mp4"
            })
        else:
            return jsonify({"status": "erro", "mensagem": "Arquivo gerado é inválido ou vazio"}), 500

    except Exception as e:
        logger.error(f"[EXCEÇÃO CRÍTICA] {str(e)}")
        return jsonify({"status": "erro", "detalhe": str(e)}), 500

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(TEMP_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=porta)
