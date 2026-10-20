import os
import sys
import time
import json
import traceback

print("=== [1/6] INICIANDO SCRIPT PRINCIPAL ===", flush=True)

try:
    print("=== [2/6] CARREGANDO DEPENDÊNCIAS DO GOOGLE E FFMPEG ===", flush=True)
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    print("-> Bibliotecas importadas com sucesso!", flush=True)
except Exception as e:
    print(f"CRÍTICO: Erro ao importar bibliotecas: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

def autenticar_drive():
    print("=== [3/6] AUTENTICANDO COM O GOOGLE DRIVE ===", flush=True)
    try:
        service_account_info = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not service_account_info:
            raise ValueError("A variável de ambiente GOOGLE_SERVICE_ACCOUNT_JSON não foi encontrada.")
        
        creds_dict = json.loads(service_account_info)
        scopes = ['https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        service = build('drive', 'v3', credentials=creds)
        
        print("-> Autenticação no Google Drive concluída com sucesso!", flush=True)
        return service
    except Exception as e:
        print(f"CRÍTICO: Erro na autenticação do Google Drive: {e}", flush=True)
        traceback.print_exc()
        return None

def enviar_para_drive(service, caminho_arquivo, folder_id):
    """Função para enviar vídeo para a pasta designada sem enviar e-mails de notificação."""
    try:
        nome_arquivo = os.path.basename(caminho_arquivo)
        file_metadata = {
            'name': nome_arquivo,
            'parents': [folder_id]
        }
        media = MediaFileUpload(caminho_arquivo, resumable=True)
        
        print(f"A enviar '{nome_arquivo}' para o Google Drive...", flush=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            sendNotificationEmail=False  # Mantém o upload totalmente silencioso
        ).execute()
        
        print(f"-> Upload concluído com sucesso! ID no Drive: {file.get('id')}", flush=True)
    except Exception as e:
        print(f"Erro ao enviar arquivo para o Drive: {e}", flush=True)

def loop_principal():
    print("=== [4/6] INICIALIZANDO O SERVIÇO DO DRIVE ===", flush=True)
    drive_service = autenticar_drive()
    
    if not drive_service:
        print("CRÍTICO: Não foi possível conectar ao Drive. Encerrando execução.", flush=True)
        sys.exit(1)
        
    # ID da sua pasta no Google Drive (substitua caso necessário ou deixe parametrizado)
    FOLDER_ID = "SEU_FOLDER_ID_AQUI" 
        
    print("=== [5/6] ENTRANDO NO LOOP CONTINUO DO ROBÔ ===", flush=True)
    
    ciclo = 1
    while True:
        print(f"--- [CICLO {ciclo}] Verificando/Gerando novos vídeos... ---", flush=True)
        
        # 1. Aqui entra a sua lógica de processamento / FFmpeg para gerar o vídeo
        # Exemplo: os.system("ffmpeg ...")
        
        # 2. Aqui entra o envio do vídeo gerado:
        # if os.path.exists("video_gerado.mp4"):
        #     enviar_para_drive(drive_service, "video_gerado.mp4", FOLDER_ID)
        
        print(f"--- [CICLO {ciclo}] Concluído. Aguardando próximo intervalo... ---", flush=True)
        ciclo += 1
        time.sleep(300) # Intervalo de 5 minutos entre os ciclos

if __name__ == "__main__":
    print("=== [6/6] EXECUÇÃO DO BLOCO MAIN ===", flush=True)
    loop_principal()
