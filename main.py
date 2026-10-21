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
