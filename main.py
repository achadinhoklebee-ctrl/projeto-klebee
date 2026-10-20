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

# E-mail da sua conta para acesso às pastas/arquivos do robô
EMAIL_PROPRIETARIO = "achadinho.klebee@gmail.com"

def obter_credenciais():
    if os.path.exists("service_account.json"):
        return service_account.Credentials.from_service_account_file(
            "service_account.json", scopes=["https://www.googleapis.com/auth/drive"]
        )
    
    service_account_env = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if service_account_env:
        info = json.loads(service_account_env)
        return service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive"]
        )

    print("[Google Drive] Erro: Nenhuma credencial encontrada.")
    sys.stdout.flush()
    return None

def obter_ou_criar_pasta_destino(service):
    """Procura se a pasta já existe. Se não existir, cria uma única vez sem enviar e-mails."""
    try:
        # Procura se o robô já possui a pasta criada
        query = "name = 'Fabrica_Videos_Shopee_Robot' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])
        
        if files:
            # Reutiliza a pasta existente sem criar nada de novo nem mandar e-mail
            return files[0]['id']

        # Caso não exista nenhuma, cria a pasta autónoma
        file_metadata = {
            'name': 'Fabrica_Videos_Shopee_Robot',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        nova_pasta_id = folder.get('id')
        print(f"[Google Drive] Pasta criada pelo robô! ID: {nova_pasta_id}")
        
        # Compartilha com seu e-mail com SENDNOTIFICATIONEMAIL=FALSE (SEM NOTIFICAÇÃO POR E-MAIL)
        user_permission = {
            'type': 'user',
            'role': 'writer',
            'emailAddress': EMAIL_PROPRIETARIO
        }
        service.permissions().create(
            fileId=nova_pasta_id,
            body=user_permission,
            sendNotificationEmail=False,  # <--- BLOQUEIA O ENVIO DE E-MAILS
            fields='id'
        ).execute()
        
        return nova_pasta_id
    except Exception as e:
        print(f"[Google Drive] Erro ao gerir pasta autónoma: {e}")
        sys.stdout.flush()
        return None

def enviar_para_drive(caminho_arquivo, nome_arquivo):
    creds = obter_credenciais()
    if not creds:
        return

    try:
        service = build('drive', 'v3', credentials=creds)
        folder_id = obter_ou_criar_pasta_destino(service)
        
        if not folder_id:
            print("[Google Drive] Erro: Não foi possível obter pasta de destino.")
            sys.stdout.flush()
            return

        caminho_absoluto = os.path.abspath(caminho_arquivo)

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
        
        print(f"[Google Drive] Vídeo enviado silenciosamente! ID no Drive: {file.get('id')}")
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
