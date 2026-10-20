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

def loop_principal():
    print("=== [4/6] INICIALIZANDO O SERVIÇO DO DRIVE ===", flush=True)
    drive_service = autenticar_drive()
    
    if not drive_service:
        print("CRÍTICO: Não foi possível conectar ao Drive. Encerrando execução.", flush=True)
        sys.exit(1)
        
    print("=== [5/6] ENTRANDO NO LOOP CONTINUO DO ROBÔ ===", flush=True)
    
    ciclo = 1
    while True:
        print(f"--- [CICLO {ciclo}] Processando vídeos / Verificando fila... ---", flush=True)
        
        # Adicione aqui as suas chamadas de geração/renderização com FFmpeg e upload
        # Exemplo de log de status:
        print(f"--- [CICLO {ciclo}] Aguardando próximo intervalo... ---", flush=True)
        
        ciclo += 1
        time.sleep(60) # Intervalo de 60 segundos entre as verificações

if __name__ == "__main__":
    print("=== [6/6] EXECUÇÃO DO BLOCO MAIN ===", flush=True)
    loop_principal()
