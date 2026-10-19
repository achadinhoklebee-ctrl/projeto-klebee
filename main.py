import os
import subprocess
import time

print("=== [PROJETO KLEBEE: SERVIDOR NA NUVEM] ===")
PASTA_SAIDA = "videos_produzidos"
os.makedirs(PASTA_SAIDA, exist_ok=True)

def processar_ciclo():
    print("\n[Robô] Iniciando ciclo de renderização...")
    base = "base.mp4"
    final = os.path.join(PASTA_SAIDA, f"VIDEO_{int(time.time())}.mp4")

    # Gera vídeo base vertical
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=navy:s=1080x1920:d=10", "-c:v", "libx264", "-pix_fmt", "yuv420p", base], check=True)
    
    # Aplica tratamento visual e headline
    subprocess.run(["ffmpeg", "-y", "-i", base, "-vf", "hflip,drawtext=text='ACHADINHO IMPERDÍVEL!':fontcolor=yellow:fontsize=50:x=(w-text_w)/2:y=250:box=1:boxcolor=black@0.8", "-c:v", "libx264", "-pix_fmt", "yuv420p", final], check=True)
    
    print(f"[✓] Vídeo gerado com sucesso!")

if __name__ == "__main__":
    while True:
        try:
            processar_ciclo()
        except Exception as e:
            print(f"Erro: {e}")
        time.sleep(3600)
