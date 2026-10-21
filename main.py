import os
import logging
import subprocess
import urllib.request
from flask import Flask, jsonify, request, send_from_directory
from gtts import gTTS

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização obrigatória do Flask antes de qualquer rota
app = Flask(__name__)

TEMP_DIR = "/tmp"

@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "mensagem": "Projeto Klebee - API de Geração de Vídeos Reais Ativa (Etapa 1)"
    })

@app.route("/gerar-video-real", methods=["GET", "POST"])
def gerar_video_real():
    try:
        # Suporte a parâmetros via GET (query string) ou JSON (POST)
        if request.is_json:
            data = request.get_json()
        else:
            data = request.args

        url_video = data.get("url_video")
        headline = data.get("headline", "ACHADINHO IMPERDÍVEL 😱")
        texto_narração = data.get("texto", "Olha esse produto incrível que eu separei para você! Corre para garantir o seu clicando no link da sacolinha.")

        if not url_video:
            return jsonify({
                "status": "erro",
                "mensagem": "Parâmetro 'url_video' é obrigatório. Forneça o link de origem do vídeo do produto."
            }), 400

        logger.info(f"[WORKER] Iniciando processamento para headline: '{headline}' | URL: {url_video}")

        video_original = os.path.join(TEMP_DIR, "input_produto.mp4")
        audio_path = os.path.join(TEMP_DIR, "narracao.mp3")
        legenda_path = os.path.join(TEMP_DIR, "legenda.srt")
        video_final = os.path.join(TEMP_DIR, "video_final_afiliado.mp4")

        # Limpeza prévia de arquivos temporários
        for f in [video_original, audio_path, legenda_path, video_final]:
            if os.path.exists(f):
                os.remove(f)

        # 1. Download do vídeo real do produto com cabeçalhos de segurança
        logger.info("[BAIXANDO] Baixando mídia do produto...")
        req = urllib.request.Request(
            url_video,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        try:
            with urllib.request.urlopen(req) as response, open(video_original, 'wb') as out_file:
                out_file.write(response.read())
        except Exception as e:
            logger.error(f"[ERRO DOWNLOAD] Falha ao baixar o vídeo da URL fornecida: {str(e)}")
            return jsonify({
                "status": "erro",
                "mensagem": f"Não foi possível baixar o vídeo da URL fornecida. Detalhe: {str(e)}"
            }), 400

        # 2. Síntese da narração comercial em português brasileiro (gTTS)
        logger.info("[TTS] Gerando narração em português...")
        tts = gTTS(text=texto_narração, lang="pt")
        tts.save(audio_path)

        # 3. Griação automática de arquivo de legendas simples sincronizadas (SRT)
        # Dividindo o texto básico em blocos de tempo para exibição na tela
        logger.info("[LEGENDA] Gerando arquivo SRT sincronizado...")
        conteudo_srt = (
            "1\n00:00:00,000 --> 00:00:04,500\n" + texto_narração[:45] + "\n\n"
            "2\n00:00:04,500 --> 00:00:09,000\n" + texto_narração[45:90] + "\n\n"
            "3\n00:00:09,000 --> 00:00:15,000\n" + texto_narração[90:] if len(texto_narração) > 90 else
            "1\n00:00:00,000 --> 00:00:05,000\n" + texto_narração
        )
        with open(legenda_path, "w", encoding="utf-8") as f_srt:
            f_srt.write(conteudo_srt)

        # 4. Construção do filtro complexo do FFmpeg:
        # - Redimensionamento e corte para formato vertical 9:16 (1080x1920)
        # - Inclusão de faixa preta semi-transparente e texto da Headline no topo
        # - Inclusão de legendas dinâmicas na parte inferior
        # - Ducking de áudio (redução do som original para 20% e áudio da narração em 100%)
        
        # Nota: O filtro subtitles do FFmpeg exige caminhos normalizados sem caracteres especiais complexos no path
        subtitles_filter = f"subtitles={legenda_path}:force_style='FontName=Arial,FontSize=24,PrimaryColour=&H00FFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2,Alignment=2'"
        
        filtro_complexo = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"drawbox=y=60:w=1080:h=140:color=black@0.6:t=fill,"
            f"drawtext=text='{headline}':fontcolor=yellow:fontsize=50:x=(w-text_w)/2:y=100,"
            f"{subtitles_filter}[v_out];"
            "[0:a]volume=0.2[a1];[1:a]volume=1.0[a2];[a1][a2]amix=inputs=2:duration=first[aout]"
        )

        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-i", video_original,
            "-i", audio_path,
            "-filter_complex", filtro_complexo,
            "-map", "[v_out]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-t", "15",  # Duração alvo de 15 segundos
            "-shortest",
            video_final
        ]

        logger.info("[FFMPEG] Renderizando vídeo vertical com headline, legendas e ducking...")
        res_ffmpeg = subprocess.run(cmd_ffmpeg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if res_ffmpeg.returncode != 0:
            logger.error(f"[FFMPEG ERRO] {res_ffmpeg.stderr}")
            return jsonify({
                "status": "erro",
                "mensagem": "Falha na renderização do FFmpeg",
                "detalhe": res_ffmpeg.stderr[-600:]
            }), 500

        # 5. Validação rigorosa do arquivo gerado via ffprobe e checagens estruturais
        if not os.path.exists(video_final) or os.path.getsize(video_final) == 0:
            return jsonify({"status": "erro", "mensagem": "Arquivo MP4 gerado não existe ou está vazio."}), 500

        # Validação detalhada com ffprobe
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=codec_type",
            "-of", "default=noprint_wrappers=1",
            video_final
        ]
        probe_res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        logger.info(f"[VALIDAÇÃO FFPROBE] Resultado:\n{probe_res.stdout}")

        if "codec_type=video" not in probe_res.stdout or "codec_type=audio" not in probe_res.stdout:
            return jsonify({
                "status": "erro",
                "mensagem": "Validação falhou: o arquivo final não contém fluxos de vídeo ou áudio válidos."
            }), 500

        tamanho_bytes = os.path.getsize(video_final)
        logger.info(f"[SUCESSO] Vídeo gerado e validado com rigor! Tamanho: {tamanho_bytes} bytes")

        return jsonify({
            "status": "sucesso",
            "mensagem": "Vídeo real de produto gerado, legendado e validado com sucesso!",
            "tamanho_bytes": tamanho_bytes,
            "download": "/download/video_final_afiliado.mp4"
        })

    except Exception as e:
        logger.error(f"[EXCEÇÃO CRÍTICA] {str(e)}")
        return jsonify({"status": "erro", "detalhe": str(e)}), 500

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(TEMP_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=porta)
