import os
import subprocess
import time

print("=== [PROJETO KLEBEE: SERVIDOR NA NUVEM] ===")
PASTA_SAIDA = "videos_produzidos"
os.makedirs(PASTA_SAIDA, exist_ok=True)

def processar_ciclo():
    print("\n[Robô] Iniciando ciclo de renderização...")
    nome_video = f"VIDEO_{int(time.time())}.mp4"
    final = os.path.join(PASTA_SAIDA, nome_video)
    
    # Gera o vídeo vertical (1080x1920) com a headline diretamente
    comando_ffmpeg = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "color=c=navy:s=1080x1920:d=10",
        "-vf", "drawtext=text='ACHADINHO IMPERDÍVEL!':fontcolor=yellow:fontsize=50:x=(w-text_w)/2:y=200",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        final
    ]
    
    res = subprocess.run(comando_ffmpeg)
    
    if res.returncode == 0:
        print(f"[Robô] Vídeo gerado com sucesso: {final}")
        
        # Envio para a pasta do Google Drive
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        if folder_id:
            print(f"[Google Drive] Pasta identificada para envio: {folder_id}")
        else:
            print("[Google Drive] Variável GOOGLE_DRIVE_FOLDER_ID não configurada.")
    else:
        print("[Robô] Erro ao gerar o vídeo via FFmpeg.")

if __name__ == "__main__":
    while True:
        processar_ciclo()
        print("[Robô] Aguardando próximo ciclo (60 segundos)...")
        time.sleep(60)
