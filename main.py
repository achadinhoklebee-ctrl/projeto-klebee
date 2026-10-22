import os
import re
import uuid
import shutil
import logging
import tempfile
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request, send_from_directory, url_for
from gtts import gTTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("klebee")
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024

OUTPUT_DIR = Path(os.environ.get("KLEBEE_OUTPUT_DIR", "/tmp/klebee_outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TEXT = (
    "Olha esse produto incrível que eu separei para você! "
    "Corre para garantir o seu clicando no link da sacolinha."
)
DEFAULT_HEADLINE = "ACHADINHO IMPERDÍVEL"


def run_command(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-2500:] or "Comando de mídia falhou.")
    return result.stdout.strip()


def probe(path):
    raw = run_command([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type", "-of", "json", str(path)
    ])
    import json
    data = json.loads(raw)
    duration = float(data.get("format", {}).get("duration") or 0)
    kinds = {s.get("codec_type") for s in data.get("streams", [])}
    if duration <= 0 or "video" not in kinds:
        raise ValueError("O arquivo recebido não contém um vídeo válido.")
    return duration, kinds


def ffmpeg_escape_path(path):
    # Escape path characters for FFmpeg's subtitles filter argument.
    value = str(path).replace("\\", "/")
    value = value.replace(":", r"\\:").replace("'", r"\\'")
    value = value.replace(",", r"\\,").replace("[", r"\\[").replace("]", r"\\]")
    return value


def escape_drawtext(value):
    # Escape FFmpeg drawtext special characters.
    return (str(value).replace("\\", r"\\\\").replace(":", r"\\:")
            .replace("'", r"\\'").replace("%", r"\\%")
            .replace(",", r"\\,").replace("[", r"\\[").replace("]", r"\\]"))


def timestamp(seconds):
    ms = int(max(0, seconds) * 1000)
    hours, rem = divmod(ms, 3600000)
    minutes, rem = divmod(rem, 60000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def make_srt(text, duration, output_path):
    # Caption blocks are timed over the generated speech duration; this is not
    # forced-alignment/word-level transcription.
    words = text.split()
    if not words:
        words = [" "]
    groups = []
    current = []
    for word in words:
        current.append(word)
        if len(current) >= 7 or len(" ".join(current)) >= 38:
            groups.append(" ".join(current))
            current = []
    if current:
        groups.append(" ".join(current))
    total_chars = sum(max(1, len(g)) for g in groups)
    cursor = 0.0
    lines = []
    for index, group in enumerate(groups, start=1):
        share = duration * max(1, len(group)) / total_chars
        start = cursor
        end = duration if index == len(groups) else min(duration, cursor + share)
        lines.append(f"{index}\n{timestamp(start)} --> {timestamp(end)}\n{group}")
        cursor = end
    output_path.write_text("\n\n".join(lines) + "\n", encoding="utf-8")


@app.get("/")
def home():
    return jsonify({
        "status": "online",
        "projeto": "Super Robô Klebee",
        "etapa": "gerador de vídeo por upload de MP4",
        "upload_mp4": True
    })


@app.route("/gerar-video-real", methods=["GET", "POST"])
def gerar_video_real():
    # GET remains only as a compatibility/health hint; actual media generation
    # should use POST multipart/form-data with field 'video'.
    if request.method == "GET":
        return jsonify({
            "status": "instrucoes",
            "mensagem": "Envie um POST multipart/form-data com o arquivo no campo 'video'.",
            "campos": {"video": "arquivo .mp4", "headline": "opcional", "texto": "opcional"}
        }), 200

    job_id = uuid.uuid4().hex
    try:
        headline = (request.form.get("headline") or DEFAULT_HEADLINE).strip()[:120]
        narration = (request.form.get("texto") or DEFAULT_TEXT).strip()[:2000]
        uploaded = request.files.get("video")

        with tempfile.TemporaryDirectory(prefix=f"klebee_{job_id}_") as temp:
            work = Path(temp)
            input_video = work / "input.mp4"
            audio_path = work / "narracao.mp3"
            subtitles_path = work / "legenda.srt"
            output_temp = work / "render.mp4"

            if uploaded and uploaded.filename:
                if Path(uploaded.filename).suffix.lower() not in {".mp4", ".mov", ".m4v", ".webm"}:
                    return jsonify({"status": "erro", "mensagem": "Formato não suportado. Envie um vídeo MP4, MOV, M4V ou WEBM."}), 400
                uploaded.save(input_video)
            else:
                # Backward compatibility with direct media URLs, without attempting
                # to resolve or scrape a Shopee product page.
                url_video = (request.form.get("url_video") or "").strip()
                parsed = urlparse(url_video)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    return jsonify({
                        "status": "erro",
                        "mensagem": "Envie um arquivo no campo 'video' ou uma URL direta de arquivo de mídia em 'url_video'. Link de página de produto ainda não é suportado."
                    }), 400
                req = Request(url_video, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(req, timeout=45) as response, input_video.open("wb") as out:
                    shutil.copyfileobj(response, out, length=1024 * 1024)

            if not input_video.exists() or input_video.stat().st_size == 0:
                return jsonify({"status": "erro", "mensagem": "O vídeo enviado está vazio."}), 400

            original_duration, stream_kinds = probe(input_video)
            logger.info("[%s] Vídeo recebido (%.2fs); streams=%s", job_id, original_duration, stream_kinds)

            logger.info("[%s] Gerando narração em português", job_id)
            gTTS(text=narration, lang="pt-br").save(str(audio_path))
            speech_duration, speech_kinds = probe(audio_path)
            if "audio" not in speech_kinds:
                raise RuntimeError("A narração gerada não contém áudio.")

            make_srt(narration, speech_duration, subtitles_path)
            subtitle_arg = ffmpeg_escape_path(subtitles_path)
            subtitle_filter = (
                f"subtitles='{subtitle_arg}':force_style="
                "'FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,"
                "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,Alignment=2'"
            )
            video_filter = (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                "drawbox=x=0:y=45:w=iw:h=150:color=black@0.60:t=fill,"
                f"drawtext=text='{escape_drawtext(headline)}':fontcolor=yellow:"
                "fontsize=48:x=(w-text_w)/2:y=95,"
                f"{subtitle_filter}"
            )

            cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(input_video), "-i", str(audio_path)]
            if "audio" in stream_kinds:
                audio_filter = (
                    "[0:a]volume=0.20[original];"
                    "[1:a]volume=1.0[voice];"
                    "[original][voice]amix=inputs=2:duration=longest:dropout_transition=2[aout]"
                )
                cmd += ["-filter_complex", f"[0:v]{video_filter}[vout];{audio_filter}",
                        "-map", "[vout]", "-map", "[aout]"]
            else:
                cmd += ["-vf", video_filter, "-map", "0:v:0", "-map", "1:a:0"]
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-t", "15", "-movflags", "+faststart", str(output_temp)]

            logger.info("[%s] Iniciando FFmpeg", job_id)
            run_command(cmd)
            final_name = f"klebee_{job_id}.mp4"
            final_path = OUTPUT_DIR / final_name
            shutil.copy2(output_temp, final_path)
            final_duration, final_streams = probe(final_path)
            if "video" not in final_streams or "audio" not in final_streams:
                final_path.unlink(missing_ok=True)
                raise RuntimeError("O MP4 final não contém os fluxos de áudio e vídeo esperados.")

            logger.info("[%s] Render concluído: %s bytes, %.2fs", job_id, final_path.stat().st_size, final_duration)
            return jsonify({
                "status": "sucesso",
                "mensagem": "MP4 renderizado e validado estruturalmente.",
                "job_id": job_id,
                "duracao_segundos": round(final_duration, 2),
                "tamanho_bytes": final_path.stat().st_size,
                "observacao": "As legendas são distribuídas ao longo da duração da narração; sincronização palavra a palavra ainda não foi implementada.",
                "download": url_for("download_file", filename=final_name, _external=True)
            }), 200

    except Exception as exc:
        logger.exception("[%s] Falha ao gerar vídeo", job_id)
        return jsonify({"status": "erro", "job_id": job_id, "mensagem": str(exc)[-2000:]}), 500


@app.get("/download/<filename>")
def download_file(filename):
    if not re.fullmatch(r"klebee_[a-f0-9]{32}\.mp4", filename):
        return jsonify({"status": "erro", "mensagem": "Nome de arquivo inválido."}), 400
    path = OUTPUT_DIR / filename
    if not path.is_file():
        return jsonify({"status": "erro", "mensagem": "Vídeo não encontrado ou expirado."}), 404
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True, mimetype="video/mp4")


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"status": "erro", "mensagem": "Arquivo acima do limite de 300 MB."}), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
