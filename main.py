import os
import subprocess
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

print("=== [PROJETO KLEBEE: SERVIDOR NA NUVEM COM GOOGLE DRIVE] ===")
PASTA_SAIDA = "videos_produzidos"
os.makedirs(PASTA_SAIDA, exist_ok=True)

def enviar_para_drive(caminho_arquivo, nome_arquivo):
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        print("[Google Drive] Erro: GOOGLE_DRIVE_FOLDER_ID não configurada.")
        return

    try:
        # Nota: O Railway lê credenciais se configuradas por variáveis ou arquivo de chave json
        creds = None
        # Se houver um arquivo de credenciais local no Railway (ex: service_account.json)
        if os.path.exists("service_account.json"):
            creds = service_account.Credentials.from_service_account_file(
                "service_account.json", scopes=["https://www.googleapis.com/auth/drive"]
            )
        else:
            # Tenta autenticação padrão do ambiente se aplicável
            creds = service_account.Credentials.from_service_account_info(
                os.environ, scopes=["https://www.googleapis.com/auth/drive"]
            )

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
        print(f"[Google Drive] Erro no upload: {e}")

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
        # Envia o vídeo gerado para o Google Drive
        enviar_para_drive(final, nome_video)
    else:
        print("[Robô] Erro ao gerar o vídeo via FFmpeg.")

if __name__ == "__main__":
    while True:
        processar_ciclo()
        print("[Robô] Aguardando próximo ciclo (60 segundos)...")
        time.sleep(60)
