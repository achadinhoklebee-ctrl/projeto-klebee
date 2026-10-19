import os
import json
import subprocess
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

print("=== [PROJETO KLEBEE: SERVIDOR NA NUVEM COM GOOGLE DRIVE] ===")
PASTA_SAIDA = "videos_produzidos"
os.makedirs(PASTA_SAIDA, exist_ok=True)

def obter_credenciais():
    # 1. Tenta carregar do arquivo local service_account.json se existir
    if os.path.exists("service_account.json"):
        print("[Google Drive] Usando arquivo service_account.json local.")
        return service_account.Credentials.from_service_account_file(
            "service_account.json", scopes=["https://www.googleapis.com/auth/drive"]
        )
    
    # 2. Tenta carregar da variável de ambiente GOOGLE_SERVICE_ACCOUNT_JSON
    service_account_env = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if service_account_env:
        print("[Google Drive] Usando variável GOOGLE_SERVICE_ACCOUNT_JSON.")
        info = json.loads(service_account_env)
        return service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive"]
        )

    print("[Google Drive] Erro: Nenhuma credencial encontrada (arquivo service_account.json ou variável GOOGLE_SERVICE_ACCOUNT_JSON em falta).")
    return None

def enviar_para_drive(caminho_arquivo, nome_arquivo):
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        print("[Google Drive] Erro: GOOGLE_DRIVE_FOLDER_ID não configurada.")
        return

    creds = obter_credenciais()
    if not creds:
        return

    try:
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': nome_arquivo,
            'parents': [folder_id]
        }
        media = MediaFileUpload(caminho_arquivo, mimetype='video/mp4')
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        print(f"[Google Drive] Vídeo enviado com sucesso! ID no Drive: {file.get('id')}")
    except Exception as e:
        print(f"[Google Drive] Erro detalhado no upload: {e}")

def processar_ciclo():
    print("\n[Robô] Iniciando ciclo de renderização...")
    nome_video = f"VIDEO_{int(time.time())}.mp4"
    final = os.path.join(PASTA_SAIDA, nome_video)
    
    # Gera o vídeo vertical (1080x1920)
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
        # Envia o vídeo gerado para o Google Drive
        enviar_para_drive(final, nome_video)
    else:
        print("[Robô] Erro ao gerar o vídeo via FFmpeg.")

if __name__ == "__main__":
    while True:
        processar_ciclo()
        print("[Robô] Aguardando próximo ciclo (60 segundos)...")
        time.sleep(60)
