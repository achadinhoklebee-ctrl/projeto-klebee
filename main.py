import os
import sys
import time
import json
import subprocess
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

def enviar_para_drive(service, caminho_arquivo, folder_id, seu_email="achadinho.klebee@gmail.com"):
    """Envia o arquivo e altera as permissões para garantir visibilidade."""
    try:
        nome_arquivo = os.path.basename(caminho_arquivo)
        
        file_metadata = {
            'name': nome_arquivo,
            'parents': [folder_id] if folder_id else []
        }
            
        media = MediaFileUpload(caminho_arquivo, mimetype='video/mp4', resumable=True)
        
        print(f"A ENVIAR PARA O DRIVE: '{nome_arquivo}'...", flush=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink',
            supportsAllDrives=True
        ).execute()
        
        file_id = file.get('id')
        print(f"-> UPLOAD CONCLUÍDO! ID: {file_id}", flush=True)

        # FORÇAR PERMISSÃO DE LEITURA/ESCRITA PARA O SEU EMAIL PESSOAL
        try:
            permission = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': seu_email
            }
            service.permissions().create(
                fileId=file_id,
                body=permission,
                fields='id',
                supportsAllDrives=True
            ).execute()
            print(f"-> Permissão concedida com sucesso para {seu_email}!", flush=True)
        except Exception as perm_err:
            print(f"Aviso ao definir permissão do ficheiro: {perm_err}", flush=True)

        print(f"-> LINK DIRETO DO VÍDEO: {file.get('webViewLink')}", flush=True)
    except Exception as e:
        print(f"CRÍTICO: Erro no upload para o Drive: {e}", flush=True)
        traceback.print_exc()

def gerar_video_ffmpeg(nome_saida="video_shopee.mp4"):
    print(f"Renderizando vídeo via FFmpeg: {nome_saida}", flush=True)
    
    comando = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=navy:s=1080x1920:d=5",
        "-vf", "drawtext=text='ACHADINHOS SHOPEE':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        nome_saida
    ]
    
    try:
        resultado = subprocess.run(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if resultado.returncode == 0:
            print("-> Vídeo gerado com sucesso pelo FFmpeg!", flush=True)
            return True
        else:
            print(f"Erro no FFmpeg: {resultado.stderr}", flush=True)
            return False
    except Exception as e:
        print(f"Exceção ao executar FFmpeg: {e}", flush=True)
        return False

def loop_principal():
    print("=== [4/6] INICIALIZANDO O SERVIÇO DO DRIVE ===", flush=True)
    drive_service = autenticar_drive()
    
    if not drive_service:
        print("CRÍTICO: Não foi possível conectar ao Drive. Encerrando execução.", flush=True)
        sys.exit(1)
        
    FOLDER_ID = "1mEKp9mdgKE-owpBIb032rLPojnxKlpaD" 
    MEU_EMAIL = "achadinho.klebee@gmail.com"
        
    print("=== [5/6] ENTRANDO NO LOOP CONTINUO DO ROBÔ ===", flush=True)
    
    ciclo = 1
    while True:
        print(f"\n--- [CICLO {ciclo}] Gerando e enviando vídeo ---", flush=True)
        
        arquivo_video = f"shopee_video_{ciclo}.mp4"
        
        if gerar_video_ffmpeg(arquivo_video):
            enviar_para_drive(drive_service, arquivo_video, FOLDER_ID, MEU_EMAIL)
            if os.path.exists(arquivo_video):
                os.remove(arquivo_video)
                print(f"-> Vídeo local {arquivo_video} limpo com sucesso.", flush=True)
                
        print(f"--- [CICLO {ciclo}] Aguardando próximo intervalo... ---", flush=True)
        ciclo += 1
        time.sleep(60)

if __name__ == "__main__":
    print("=== [6/6] EXECUÇÃO DO BLOCO MAIN ===", flush=True)
    loop_principal()
