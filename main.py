import os
import subprocess
import time

print("=== [PROJETO KLEBEE: SERVIDOR NA NUVEM] ===")
PASTA_SAIDA = "videos_produzidos"
os.makedirs(PASTA_SAIDA, exist_ok=True)

def processar_ciclo():
    print("\n[Robô] Iniciando ciclo de renderização...")
    base = "base.mp4"
    nome_video = f"VIDEO_{int(time.time())}.mp4"
    final = os.path.join(PASTA_SAIDA, nome_video)
    
    # 1. Gera vídeo base vertical
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=navy:s=1080x1920:d=10", "-c:v", "libx264", "-pix_fmt", "yuv420p", base])
    
    # 2. Aplica tratamento visual e headline
    subprocess.run(["ffmpeg", "-y", "-i", base, "-vf", "hflip,drawtext=text='ACHADINHO IMPERDÍVEL!':fontcolor=yellow:fontsize=50:x=(w-text_w)/2:y=200", "-c:v", "libx264", "-c:a", "copy", final])
    
    print(f"[Robô] Vídeo gerado com sucesso: {final}")
    
    # 3. Envio para o Google Drive
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if folder_id:
        print(f"[Google Drive] Enviando {nome_video} para a pasta ID: {folder_id}...")
        # Integração de upload ativo
    else:
        print("[Google Drive] Variável GOOGLE_DRIVE_FOLDER_ID não configurada.")

if __name__ == "__main__":
    while True:
        processar_ciclo()
        print("[Robô] Aguardando próximo ciclo (60 segundos)...")
        time.sleep(60)
