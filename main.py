import os
import json
import subprocess
import time
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

print("=== [PROJETO KLEBEE: SERVIDOR NA NUVEM COM GOOGLE DRIVE] ===")
sys.stdout.flush()

PASTA_SAIDA = "videos_produzidos"
os.makedirs(PASTA_SAIDA, exist_ok=True)

def obter_credenciais():
    if os.path.exists("service_account.json"):
        print("[Google Drive] Usando arquivo service_account.json local.")
        sys.stdout.flush()
        return service_account.Credentials.from_service_account_file(
            "service_account.json", scopes=["https://www.googleapis.com/auth/drive"]
        )
    
    service_account_env = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if service_account_env:
        print("[Google Drive] Usando variável GOOGLE_SERVICE_ACCOUNT_JSON.")
        sys.stdout.flush()
        info = json.loads(service_account_env)
        return service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive"]
        )

    print("[Google Drive] Erro: Nenhuma credencial encontrada.")
    sys.stdout.flush()
    return None

def enviar_para_drive(caminho_arquivo, nome_arquivo):
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        print("[Google Drive] Erro: GOOGLE_DRIVE_FOLDER_ID não configurada.")
        sys.stdout.flush()
        return

    creds = obter_credenciais()
    if not creds:
        return

    try:
        service = build('drive', 'v3', credentials=creds)

        caminho_absoluto = os.path.abspath(caminho_arquivo)
        print(f"[Google Drive] Preparando upload do arquivo: {caminho_absoluto}")
        sys.stdout.flush()

        file_metadata = {
            'name': nome_arquivo,
            'parents': [folder_id]
        }
        media = MediaFileUpload(caminho_absoluto, mimetype='video/mp4', resumable=True)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        print(f"[Google Drive] Vídeo enviado com sucesso! ID no Drive: {file.get('id')}")
        sys.stdout.flush()
    except Exception as e:
        print(f"[Google Drive] Erro detalhado no upload: {e}")
        sys.stdout.flush()

def processar_ciclo():
    print("\n[Robô] Iniciando ciclo de renderização...")
    sys.stdout.flush()
    
    nome_video = f"VIDEO_{int(time.time())}.mp4"
    final = os.path.join(PASTA_SAIDA, nome_video)
    
    comando_ffmpeg = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "color=c=navy:s=1080x1920:d=10",
        "-vf", "drawtext=text='ACHADINHO IMPERDÍVEL!':fontcolor=yellow:fontsize=50:x=(w-text_w)/2:y=200",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        final
    ]
    
    res = subprocess.run(comando_ffmpeg)
    
    if res.returncode == 0:
        print(f"[Robô] Vídeo gerado com sucesso: {final}")
        sys.stdout.flush()
        enviar_para_drive(final, nome_video)
    else:
        print("[Robô] Erro ao gerar o vídeo via FFmpeg.")
        sys.stdout.flush()

if __name__ == "__main__":
    while True:
        processar_ciclo()
        print("[Robô] Aguardando próximo ciclo (60 segundos)...")
        sys.stdout.flush()
        time.sleep(60)
