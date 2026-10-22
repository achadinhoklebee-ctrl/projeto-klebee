import os
import logging
import subprocess
import urllib.request
import uuid
import shutil
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from klebee_tts import generate_narration_with_timestamps

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização obrigatória do Flask antes de qualquer rota
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_MB", "200")) * 1024 * 1024

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
        # Aceita JSON/GET com URL e multipart/form-data com upload direto.
        if request.is_json:
            data = request.get_json() or {}
        elif request.form:
            data = request.form
        else:
            data = request.args

        uploaded_video = request.files.get("video")
        url_video = data.get("url_video")
        headline = data.get("headline", "ACHADINHO IMPERDÍVEL 😱")
        texto_narração = data.get("texto", "Olha esse produto incrível que eu separei para você! Corre para garantir o seu clicando no link da sacolinha.")

        if not url_video and not uploaded_video:
            return jsonify({
                "status": "erro",
                "mensagem": "Envie um arquivo no campo 'video' (multipart/form-data) ou informe 'url_video'."
            }), 400
        if uploaded_video and not uploaded_video.filename:
            return jsonify({"status": "erro", "mensagem": "O arquivo enviado não tem nome válido."}), 400

        origem = "upload" if uploaded_video else "URL"
        logger.info(f"[WORKER] Iniciando processamento para headline: '{headline}' | origem: {origem}")

        # Diretório exclusivo por requisição: impede colisões entre renderizações.
        task_id = str(uuid.uuid4())
        task_dir = os.path.join(TEMP_DIR, f"klebee_task_{task_id}")
        os.makedirs(task_dir, exist_ok=False)
        video_original = os.path.join(task_dir, "input_produto.mp4")
        audio_path = os.path.join(task_dir, "narracao.mp3")
        legenda_path = os.path.join(task_dir, "legenda.srt")
        captions_path = os.path.join(task_dir, "captionSegments.json")
        video_final = os.path.join(task_dir, "video_final_afiliado.mp4")

        # 1. Recebe o arquivo enviado diretamente ou baixa a URL fornecida.
        try:
            if uploaded_video:
                logger.info("[UPLOAD] Salvando vídeo enviado pelo usuário...")
                uploaded_video.save(video_original)
            else:
                logger.info("[BAIXANDO] Baixando mídia do produto por URL...")
                req = urllib.request.Request(
                    url_video,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=60) as response, open(video_original, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
            if not os.path.isfile(video_original) or os.path.getsize(video_original) == 0:
                raise ValueError("O vídeo recebido está vazio.")
        except Exception as e:
            logger.error(f"[ERRO ENTRADA] Falha ao receber o vídeo: {str(e)}")
            return jsonify({
                "status": "erro",
                "mensagem": f"Não foi possível receber o vídeo. Detalhe: {str(e)}"
            }), 400

        # 2. Voz neural brasileira + marcações reais de cada palavra emitidas pelo Edge-TTS.
        logger.info("[TTS] Gerando narração e timestamps WordBoundary...")
        caption_segments = generate_narration_with_timestamps(
            texto_narração, audio_path, captions_path, "pt-BR-FranciscaNeural"
        )

        # 3. SRT de compatibilidade para o pipeline FFmpeg, derivado dos timestamps reais.
        def srt_time(ms):
            ms = max(0, int(ms))
            hours, rem = divmod(ms, 3_600_000)
            minutes, rem = divmod(rem, 60_000)
            seconds, millis = divmod(rem, 1_000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

        srt_blocks = []
        for index, cue in enumerate(caption_segments, start=1):
            srt_blocks.append(
                f"{index}\n{srt_time(cue['startMs'])} --> {srt_time(cue['endMs'])}\n{cue['text']}\n"
            )
        with open(legenda_path, "w", encoding="utf-8") as f_srt:
            f_srt.write("\n".join(srt_blocks))

        # 4. Renderização pela composição Remotion (headlines animadas + legendas palavra a palavra).
        # O script de renderização usa os timestamps reais gerados pelo Edge-TTS.
        render_cmd = [
            "npm", "run", "render:klebee", "--",
            video_original, audio_path, captions_path, video_final,
            headline,
            data.get("middle_headline", "PRATICIDADE NO DIA A DIA"),
            data.get("cta_headline", "VEJA NA SHOPEE")
        ]
        logger.info("[REMOTION] Renderizando vídeo vertical com headlines animadas e legendas sincronizadas...")
        res_render = subprocess.run(
            render_cmd, cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=900
        )
        if res_render.returncode != 0:
            logger.error("[REMOTION ERRO] %s\n%s", res_render.stdout[-3000:], res_render.stderr[-5000:])
            return jsonify({
                "status": "erro",
                "mensagem": "Falha na renderização Remotion",
                "detalhe": (res_render.stderr or res_render.stdout)[-1500:]
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
            "download": f"/download/{task_id}/video_final_afiliado.mp4",
            "caption_segments": caption_segments,
            "task_id": task_id
        })

    except Exception as e:
        logger.error(f"[EXCEÇÃO CRÍTICA] {str(e)}")
        return jsonify({"status": "erro", "detalhe": str(e)}), 500

@app.route("/download/<task_id>/<filename>")
def download_file(task_id, filename):
    # Accept only the generated task directory and a plain filename.
    if not task_id.startswith("klebee_") and len(task_id) != 36:
        return jsonify({"status": "erro", "mensagem": "Identificador de tarefa inválido."}), 400
    if filename not in {"video_final_afiliado.mp4"}:
        return jsonify({"status": "erro", "mensagem": "Arquivo não permitido."}), 400
    task_dir = os.path.join(TEMP_DIR, f"klebee_task_{task_id}")
    return send_from_directory(task_dir, filename, as_attachment=True)

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=porta)
