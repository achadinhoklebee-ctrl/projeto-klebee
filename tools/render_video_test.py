#!/usr/bin/env python3
"""Renderizador isolado de vídeo de teste do Super Robô Klebee.

Não altera a aplicação Flask nem a branch main. Requer ffmpeg e ffprobe no PATH.
Recebe um vídeo real, uma faixa de narração já gerada e um arquivo ASS com
legendas. Os tempos das legendas devem vir de alinhamento verificado; o script
não finge produzir alinhamento automático.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(f"Comando falhou ({p.returncode}): {' '.join(cmd)}\n{p.stderr[-3000:]}")
    return p.stdout.strip()


def probe(path: Path, require_video: bool = True) -> dict:
    data = json.loads(run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=codec_type,codec_name,width,height,sample_rate,channels",
        "-of", "json", str(path)
    ]))
    streams = data.get("streams", [])
    kinds = {s.get("codec_type") for s in streams}
    duration = float(data.get("format", {}).get("duration") or 0)
    if duration <= 0 or "audio" not in kinds or (require_video and "video" not in kinds):
        raise RuntimeError(f"Arquivo inválido: duração={duration}, fluxos={kinds}")
    return data


def filter_path(path: Path) -> str:
    # FFmpeg filtergraph escaping for absolute paths.
    return str(path.resolve()).replace("\\", "/").replace(":", r"\\:").replace("'", r"\\'").replace(",", r"\\,")


def escape_drawtext(value: str) -> str:
    return (value.replace("\\", r"\\\\").replace(":", r"\\:")
            .replace("'", r"\\'").replace("%", r"\\%")
            .replace(",", r"\\,").replace("[", r"\\[").replace("]", r"\\]"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, type=Path, help="Vídeo original do produto")
    ap.add_argument("--voice", required=True, type=Path, help="Faixa de narração pronta")
    ap.add_argument("--captions-ass", required=True, type=Path, help="Legendas ASS com tempos revisados")
    ap.add_argument("--output", required=True, type=Path, help="Destino do MP4 final")
    ap.add_argument("--headline", default="VENTILADOR PORTÁTIL", help="Headline curta")
    ap.add_argument("--duration", type=float, default=15.0, help="Duração máxima do vídeo")
    args = ap.parse_args()

    for executable in ("ffmpeg", "ffprobe"):
        if not shutil.which(executable):
            raise RuntimeError(f"Dependência ausente: {executable}")
    for path in (args.video, args.voice, args.captions_ass):
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Arquivo ausente ou vazio: {path}")
    if not (1 <= args.duration <= 60):
        raise RuntimeError("--duration deve ficar entre 1 e 60 segundos")

    # Validar a entrada antes de renderizar.
    source_info = probe(args.video)
    voice_info = probe(args.voice, require_video=False)
    voice_duration = float(voice_info["format"]["duration"])
    final_duration = min(args.duration, voice_duration)
    if final_duration < 3:
        raise RuntimeError("A narração tem menos de 3 segundos; revise a faixa de áudio.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="klebee_render_") as td:
        temp_output = Path(td) / "render.mp4"
        subtitle_path = filter_path(args.captions_ass)
        headline = escape_drawtext(args.headline)
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1,eq=contrast=1.03:saturation=1.04,"
            "unsharp=5:5:0.25:3:3:0,"
            "drawbox=x=0:y=55:w=iw:h=135:color=0xF47721@0.92:t=fill,"
            f"drawtext=font='Noto Sans':text='{headline}':fontcolor=white:"
            "fontsize=48:x=(w-text_w)/2:y=96:"
            "shadowcolor=black@0.45:shadowx=2:shadowy=3,"
            f"subtitles='{subtitle_path}'"
        )
        cmd = [
            "ffmpeg", "-hide_banner", "-y", "-i", str(args.video), "-i", str(args.voice),
            "-filter_complex", f"[0:v]{vf}[v];[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]",
            "-map", "[v]", "-map", "[a]", "-t", f"{final_duration:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(temp_output)
        ]
        run(cmd)
        output_info = probe(temp_output)
        streams = output_info.get("streams", [])
        video_stream = next(s for s in streams if s.get("codec_type") == "video")
        if (video_stream.get("width"), video_stream.get("height")) != (1080, 1920):
            raise RuntimeError("O resultado não ficou em 1080x1920.")
        # Decodificação integral: não basta o arquivo existir ou ter tamanho > 0.
        run(["ffmpeg", "-v", "error", "-i", str(temp_output), "-f", "null", "-"])
        shutil.copy2(temp_output, args.output)

    final_info = probe(args.output)
    print(json.dumps({
        "status": "validado_estruturalmente",
        "output": str(args.output.resolve()),
        "size_bytes": args.output.stat().st_size,
        "duration_seconds": round(float(final_info["format"]["duration"]), 3),
        "video": next(s for s in final_info["streams"] if s.get("codec_type") == "video"),
        "audio": next(s for s in final_info["streams"] if s.get("codec_type") == "audio"),
        "note": "A validação estrutural não substitui a inspeção visual nem comprova alinhamento semântico das legendas."
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
